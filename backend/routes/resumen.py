"""Resumen (dashboard summary) route."""
from typing import Optional
from datetime import datetime, timedelta

import pandas as pd
from fastapi import APIRouter

from backend.services.loaders import (
    load_campo,
    load_comercial,
    load_empaque,
    load_finanzas,
    load_costos,
)
from backend.services.filters import (
    apply_campo_filters,
    apply_comercial_filters,
    apply_empaque_filters,
    apply_finanzas_filters,
    apply_costos_filters,
)
from backend.services.performance import cache_response
from backend.services.metrics import (
    safe_div,
    pct,
    week_label,
    month_label,
    compute_insights_comercial,
    compute_insights_empaque,
)

router = APIRouter()


@router.get("")
@router.get("/")
@cache_response("campo.csv", "empaque.csv", "comercial.csv", "finanzas.csv", "costos.csv", maxsize=192)
def get_resumen(
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    finca: Optional[str] = None,
    variedad: Optional[str] = None,
    destino: Optional[str] = None,
    cliente: Optional[str] = None,
    canal: Optional[str] = None,
):
    # Load raw data
    df_campo_raw = load_campo()
    df_emp_raw = load_empaque()
    df_com_raw = load_comercial()
    df_fin_raw = load_finanzas()
    df_cos_raw = load_costos()

    # Apply filters
    df_campo = apply_campo_filters(
        df_campo_raw,
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        variedad=variedad,
    )
    df_emp = apply_empaque_filters(
        df_emp_raw,
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
    )
    df_com = apply_comercial_filters(
        df_com_raw,
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        destino=destino,
        cliente=cliente,
        canal=canal,
    )
    df_fin = apply_finanzas_filters(
        df_fin_raw,
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    df_cos = apply_costos_filters(
        df_cos_raw,
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
    )

    # -----------------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------------
    fruta_ingresada_kg = float(df_emp["kg_ingresados"].sum()) if not df_emp.empty else 0.0
    kg_exportables = float(df_emp["kg_exportables"].sum()) if not df_emp.empty else 0.0
    kg_industria = float(df_emp["kg_industria"].sum()) if not df_emp.empty else 0.0
    kg_procesados = kg_exportables + kg_industria
    pct_exportable = round(safe_div(kg_exportables, fruta_ingresada_kg) * 100, 1)

    ventas_netas_usd = float(df_com["importe_usd"].sum()) if not df_com.empty else 0.0

    # Weighted average margin
    if not df_com.empty and "margen_estimado" in df_com.columns:
        total_imp = df_com["importe_usd"].sum()
        if total_imp > 0:
            margen_bruto_pct = round(
                float(
                    (df_com["margen_estimado"] * df_com["importe_usd"]).sum() / total_imp * 100
                ),
                1,
            )
        else:
            margen_bruto_pct = 0.0
    else:
        margen_bruto_pct = 0.0

    # Projected cash for next 30 days
    anchor_date = (
        pd.Timestamp(df_fin["fecha"].max()).to_pydatetime()
        if not df_fin.empty and "fecha" in df_fin.columns
        else datetime.today()
    )
    in_30 = anchor_date + timedelta(days=30)
    caja_proyectada_30d = 0.0
    if not df_fin.empty and "vencimiento" in df_fin.columns:
        mask = (df_fin["vencimiento"] >= pd.Timestamp(anchor_date)) & (
            df_fin["vencimiento"] <= pd.Timestamp(in_30)
        )
        fin_30 = df_fin[mask]
        if not fin_30.empty:
            ing_30 = float(
                fin_30[
                    (fin_30["tipo"] == "Ingreso")
                    & (fin_30["estado"].isin(["Cobrado", "Pendiente"]))
                ]["importe"].sum()
            )
            egr_30 = float(
                fin_30[
                    (fin_30["tipo"] == "Egreso")
                    & (fin_30["estado"].isin(["Pagado", "Pendiente"]))
                ]["importe"].sum()
            )
            caja_proyectada_30d = round(ing_30 - egr_30, 2)

    # Cost per exported kg
    costo_directo = 0.0
    if not df_cos.empty and "centro_costo" in df_cos.columns:
        costo_directo = float(
            df_cos[df_cos["centro_costo"].isin(["Campo", "Empaque", "Logística"])]["importe"].sum()
        )
    costo_kg_exportado = round(safe_div(costo_directo, kg_exportables), 4)

    # Order fulfillment
    cumplimiento_pedidos_pct = 0.0
    if not df_com.empty and "estado_pedido" in df_com.columns:
        cumplidos = (df_com["estado_pedido"] == "Cumplido").sum()
        cumplimiento_pedidos_pct = round(safe_div(int(cumplidos), len(df_com)) * 100, 1)
    elif not df_com.empty and "estado_cobro" in df_com.columns:
        cobrado = (df_com["estado_cobro"] == "Cobrado").sum()
        cumplimiento_pedidos_pct = round(safe_div(int(cobrado), len(df_com)) * 100, 1)

    kpis = {
        "fruta_ingresada_kg": round(fruta_ingresada_kg, 0),
        "kg_procesados": round(kg_procesados, 0),
        "pct_exportable": pct_exportable,
        "ventas_netas_usd": round(ventas_netas_usd, 2),
        "margen_bruto_pct": margen_bruto_pct,
        "caja_proyectada_30d": caja_proyectada_30d,
        "costo_kg_exportado": costo_kg_exportado,
        "cumplimiento_pedidos_pct": cumplimiento_pedidos_pct,
    }

    # -----------------------------------------------------------------------
    # Evolucion fruta (weekly kg_ingresados)
    # -----------------------------------------------------------------------
    evolucion_fruta = []
    if not df_emp.empty:
        weekly_fruta = (
            df_emp.groupby("semana")["kg_ingresados"].sum().reset_index().sort_values("semana")
        )
        evolucion_fruta = [
            {"semana": str(row["semana"]), "kg_ingresados": round(float(row["kg_ingresados"]), 0)}
            for _, row in weekly_fruta.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Evolucion ventas (weekly importe_usd)
    # -----------------------------------------------------------------------
    evolucion_ventas = []
    if not df_com.empty:
        weekly_ventas = (
            df_com.groupby("semana")["importe_usd"].sum().reset_index().sort_values("semana")
        )
        evolucion_ventas = [
            {"semana": str(row["semana"]), "importe_usd": round(float(row["importe_usd"]), 2)}
            for _, row in weekly_ventas.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Mix destino
    # -----------------------------------------------------------------------
    mix_destino = []
    if not df_com.empty and "destino" in df_com.columns:
        total_kg_com = float(df_com["kg_vendidos"].sum())
        dest_grp = (
            df_com.groupby("destino")["kg_vendidos"].sum().reset_index().sort_values(
                "kg_vendidos", ascending=False
            )
        )
        mix_destino = [
            {
                "destino": str(row["destino"]),
                "kg": round(float(row["kg_vendidos"]), 0),
                "pct": round(safe_div(float(row["kg_vendidos"]), total_kg_com) * 100, 1),
            }
            for _, row in dest_grp.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Margen por mes
    # -----------------------------------------------------------------------
    margen_por_mes = []
    if not df_com.empty:
        df_com_copy2 = df_com.copy()
        df_com_copy2["margen_bruto_usd"] = df_com_copy2["importe_usd"] * df_com_copy2["margen_estimado"]
        month_grp = (
            df_com_copy2.groupby("mes")
            .agg(
                ingresos_usd=("importe_usd", "sum"),
                margen_bruto_usd=("margen_bruto_usd", "sum"),
            )
            .reset_index()
            .sort_values("mes")
        )
        margen_por_mes = [
            {
                "mes": str(row["mes"]),
                "ingresos_usd": round(float(row["ingresos_usd"]), 2),
                "margen_bruto_usd": round(float(row["margen_bruto_usd"]), 2),
            }
            for _, row in month_grp.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Tabla fincas (join campo + empaque + comercial by finca)
    # -----------------------------------------------------------------------
    tabla_fincas = []
    if not df_emp.empty and "finca" in df_emp.columns:
        # Empaque aggregated by finca
        emp_finca = (
            df_emp.groupby("finca")[["kg_ingresados", "kg_exportables"]]
            .sum()
            .reset_index()
        )
        emp_finca["pct_exportable"] = emp_finca.apply(
            lambda r: round(safe_div(r["kg_exportables"], r["kg_ingresados"]) * 100, 1), axis=1
        )

        # Campo: last record per lote, then aggregate by finca
        campo_last = df_campo.sort_values("fecha").groupby(["lote", "finca"], as_index=False).last() if not df_campo.empty else pd.DataFrame()
        campo_finca = pd.DataFrame()
        if not campo_last.empty and "finca" in campo_last.columns:
            campo_finca = campo_last.groupby("finca")["kg_cosechados"].sum().reset_index()

        # Comercial by finca (if finca available)
        com_finca = pd.DataFrame()
        if not df_com.empty and "finca" in df_com.columns:
            df_com_finca = df_com.copy()
            df_com_finca["margen_ponderado"] = df_com_finca["margen_estimado"] * df_com_finca["importe_usd"]
            com_finca = (
                df_com_finca.groupby("finca")
                .agg(
                    ventas_usd=("importe_usd", "sum"),
                    margen_ponderado=("margen_ponderado", "sum"),
                )
                .reset_index()
            )
            com_finca["margen_sum"] = com_finca.apply(
                lambda r: safe_div(float(r["margen_ponderado"]), float(r["ventas_usd"])),
                axis=1,
            )

        for _, row in emp_finca.iterrows():
            f = row["finca"]
            kg_cos = 0.0
            if not campo_finca.empty and f in campo_finca["finca"].values:
                kg_cos = float(campo_finca[campo_finca["finca"] == f]["kg_cosechados"].values[0])
            ventas_usd = 0.0
            margen_p = 0.0
            if not com_finca.empty and f in com_finca["finca"].values:
                crow = com_finca[com_finca["finca"] == f].iloc[0]
                ventas_usd = float(crow["ventas_usd"])
                margen_p = round(float(crow["margen_sum"]) * 100, 1)
            tabla_fincas.append(
                {
                    "finca": str(f),
                    "kg_cosechados": round(kg_cos, 0),
                    "pct_exportable": float(row["pct_exportable"]),
                    "ventas_usd": round(ventas_usd, 2),
                    "margen_pct": margen_p,
                }
            )
        tabla_fincas.sort(key=lambda x: x["ventas_usd"], reverse=True)

    # -----------------------------------------------------------------------
    # Insights
    # -----------------------------------------------------------------------
    insights = compute_insights_comercial(df_com) + compute_insights_empaque(df_emp)
    insights = insights[:5]

    return {
        "kpis": kpis,
        "evolucion_fruta": evolucion_fruta,
        "evolucion_ventas": evolucion_ventas,
        "mix_destino": mix_destino,
        "margen_por_mes": margen_por_mes,
        "tabla_fincas": tabla_fincas,
        "insights": insights,
    }
