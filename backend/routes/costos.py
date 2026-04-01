"""Costos (costs & margins) route."""
from typing import Optional

import pandas as pd
from fastapi import APIRouter

from backend.services.loaders import load_costos, load_comercial, load_campo, load_empaque
from backend.services.filters import (
    apply_costos_filters,
    apply_comercial_filters,
    apply_campo_filters,
    apply_empaque_filters,
)
from backend.services.performance import cache_response
from backend.services.metrics import safe_div, pct, compute_insights_costos

router = APIRouter()


@router.get("")
@router.get("/")
@cache_response("costos.csv", "comercial.csv", "campo.csv", "empaque.csv", maxsize=192)
def get_costos(
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    finca: Optional[str] = None,
    lote: Optional[str] = None,
    centro_costo: Optional[str] = None,
    tipo_costo: Optional[str] = None,
    canal: Optional[str] = None,
):
    # Load and filter
    df_cos = apply_costos_filters(
        load_costos(),
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
        centro_costo=centro_costo,
        tipo_costo=tipo_costo,
        canal=canal,
    )
    df_com = apply_comercial_filters(
        load_comercial(),
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        canal=canal,
    )
    df_campo = apply_campo_filters(
        load_campo(),
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
    )
    df_emp = apply_empaque_filters(
        load_empaque(),
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
    )

    empty_kpis = {
        "costo_fruta_kg": 0.0,
        "costo_empaque_kg": 0.0,
        "costo_logistica_kg": 0.0,
        "costo_total_kg_exportado": 0.0,
        "margen_bruto_usd": 0.0,
        "margen_bruto_pct": 0.0,
        "mejor_lote": "",
        "mejor_canal": "",
    }

    if df_cos.empty:
        return {
            "kpis": empty_kpis,
            "composicion_costo": [],
            "costo_por_finca": [],
            "costo_por_lote": [],
            "costo_por_canal": [],
            "margen_por_cliente": [],
            "margen_por_destino": [],
            "tabla": [],
            "insights": ["No hay datos de costos para el período y filtros seleccionados."],
        }

    # -----------------------------------------------------------------------
    # Reference aggregates from campo and empaque (last record per lote)
    # -----------------------------------------------------------------------
    total_kg_cos_campo = 0.0
    if not df_campo.empty:
        last_campo = df_campo.sort_values("fecha").groupby(["lote", "finca"], as_index=False).last()
        total_kg_cos_campo = float(last_campo["kg_cosechados"].sum())

    total_kg_exp = float(df_emp["kg_exportables"].sum()) if not df_emp.empty else 0.0

    # -----------------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------------
    def _sum_cc(cc_name: str) -> float:
        return float(df_cos[df_cos["centro_costo"] == cc_name]["importe"].sum())

    costo_campo = _sum_cc("Campo")
    costo_empaque_cc = _sum_cc("Empaque")
    costo_logistica = _sum_cc("Logística")
    total_costos = float(df_cos["importe"].sum())
    costo_directo_total = costo_campo + costo_empaque_cc + costo_logistica

    costo_fruta_kg = round(safe_div(costo_campo, total_kg_cos_campo), 4)
    costo_empaque_kg = round(safe_div(costo_empaque_cc, total_kg_exp), 4)
    costo_logistica_kg = round(safe_div(costo_logistica, total_kg_exp), 4)
    costo_total_kg = round(safe_div(costo_directo_total, total_kg_exp), 4)

    # margen_bruto: ingresos usd - costos (convert to USD using avg tipo_cambio if available)
    ingresos_usd = float(df_com["importe_usd"].sum()) if not df_com.empty else 0.0
    # Costos are mostly ARS; compute avg exchange rate from comercial for approximate USD
    avg_tc = 1.0
    if not df_com.empty and "tipo_cambio" in df_com.columns:
        avg_tc = float(df_com["tipo_cambio"].mean())
        if avg_tc == 0:
            avg_tc = 1.0
    costos_usd = safe_div(costo_directo_total, avg_tc)
    margen_bruto_usd = round(ingresos_usd - costos_usd, 2)
    margen_bruto_pct = round(safe_div(margen_bruto_usd, ingresos_usd) * 100, 1) if ingresos_usd > 0 else 0.0

    # Best lote by margin (lowest cost/kg from costos grouped by lote)
    mejor_lote = ""
    mejor_canal = ""

    kpis = {
        "costo_fruta_kg": costo_fruta_kg,
        "costo_empaque_kg": costo_empaque_kg,
        "costo_logistica_kg": costo_logistica_kg,
        "costo_total_kg_exportado": costo_total_kg,
        "margen_bruto_usd": margen_bruto_usd,
        "margen_bruto_pct": margen_bruto_pct,
        "mejor_lote": mejor_lote,
        "mejor_canal": mejor_canal,
    }

    # -----------------------------------------------------------------------
    # Composicion costo by centro_costo
    # -----------------------------------------------------------------------
    composicion_costo = []
    if "centro_costo" in df_cos.columns:
        cc_grp = df_cos.groupby("centro_costo")["importe"].sum().reset_index().sort_values(
            "importe", ascending=False
        )
        for _, row in cc_grp.iterrows():
            composicion_costo.append(
                {
                    "tipo": str(row["centro_costo"]),
                    "importe": round(float(row["importe"]), 2),
                    "pct": round(safe_div(float(row["importe"]), total_costos) * 100, 1),
                }
            )

    # -----------------------------------------------------------------------
    # Costo por finca
    # -----------------------------------------------------------------------
    costo_por_finca = []
    if "finca" in df_cos.columns:
        finca_grp = df_cos.groupby("finca")["importe"].sum().reset_index().sort_values(
            "importe", ascending=False
        )
        # kg_exportables per finca from empaque
        emp_finca_kg = pd.DataFrame()
        if not df_emp.empty and "finca" in df_emp.columns:
            emp_finca_kg = df_emp.groupby("finca")["kg_exportables"].sum().reset_index()

        for _, row in finca_grp.iterrows():
            f = row["finca"]
            f_kg_exp = 0.0
            if not emp_finca_kg.empty and f in emp_finca_kg["finca"].values:
                f_kg_exp = float(emp_finca_kg[emp_finca_kg["finca"] == f]["kg_exportables"].values[0])
            costo_por_finca.append(
                {
                    "finca": str(f),
                    "costo_total": round(float(row["importe"]), 2),
                    "costo_kg": round(safe_div(float(row["importe"]), f_kg_exp), 4),
                }
            )

    # -----------------------------------------------------------------------
    # Costo por lote
    # -----------------------------------------------------------------------
    costo_por_lote = []
    if "lote" in df_cos.columns and "finca" in df_cos.columns:
        lote_grp = df_cos.groupby(["lote", "finca"])["importe"].sum().reset_index().sort_values(
            "importe", ascending=False
        )
        # kg_exportables per lote from empaque
        emp_lote_kg = pd.DataFrame()
        if not df_emp.empty and "lote" in df_emp.columns:
            emp_lote_kg = df_emp.groupby(["lote", "finca"])["kg_exportables"].sum().reset_index()

        for _, row in lote_grp.iterrows():
            lote_val = row["lote"]
            finca_val = row["finca"]
            l_kg_exp = 0.0
            if not emp_lote_kg.empty:
                mask = (emp_lote_kg["lote"] == lote_val) & (emp_lote_kg["finca"] == finca_val)
                if mask.any():
                    l_kg_exp = float(emp_lote_kg[mask]["kg_exportables"].values[0])
            costo_por_lote.append(
                {
                    "lote": str(lote_val),
                    "finca": str(finca_val),
                    "costo_total": round(float(row["importe"]), 2),
                    "costo_kg": round(safe_div(float(row["importe"]), l_kg_exp), 4),
                }
            )

    # -----------------------------------------------------------------------
    # Costo por canal (join with comercial for margin)
    # -----------------------------------------------------------------------
    costo_por_canal = []
    if "canal" in df_cos.columns:
        revenue_by_channel = pd.DataFrame()
        if not df_com.empty and "canal" in df_com.columns:
            revenue_by_channel = (
                df_com.groupby("canal")["importe_usd"].sum().reset_index()
            )
        revenue_total = float(revenue_by_channel["importe_usd"].sum()) if not revenue_by_channel.empty else 0.0

        direct_costs = (
            df_cos[df_cos["canal"] != "General"]
            .groupby("canal")["importe"]
            .sum()
            .reset_index()
        )
        general_cost = float(df_cos[df_cos["canal"] == "General"]["importe"].sum())

        canal_cos_grp = direct_costs.copy()
        if revenue_by_channel.empty and not canal_cos_grp.empty:
            total_direct = float(canal_cos_grp["importe"].sum())
            canal_cos_grp["importe"] = canal_cos_grp.apply(
                lambda r: float(r["importe"]) + safe_div(float(r["importe"]), total_direct) * general_cost,
                axis=1,
            )
        elif not revenue_by_channel.empty:
            if canal_cos_grp.empty:
                canal_cos_grp = revenue_by_channel.rename(columns={"importe_usd": "importe"})
                canal_cos_grp["importe"] = 0.0
            canal_cos_grp = canal_cos_grp.merge(revenue_by_channel, on="canal", how="outer").fillna(0)
            canal_cos_grp["importe"] = canal_cos_grp.apply(
                lambda r: float(r["importe"]) + safe_div(float(r["importe_usd"]), revenue_total) * general_cost,
                axis=1,
            )
        else:
            canal_cos_grp = pd.DataFrame(columns=["canal", "importe"])

        for _, row in canal_cos_grp.iterrows():
            c = row["canal"]
            ingreso_usd_c = 0.0
            if not revenue_by_channel.empty and c in revenue_by_channel["canal"].values:
                ingreso_usd_c = float(revenue_by_channel[revenue_by_channel["canal"] == c]["importe_usd"].values[0])
            costo_usd_c = safe_div(float(row["importe"]), avg_tc)
            margen_c = round(safe_div(ingreso_usd_c - costo_usd_c, ingreso_usd_c) * 100, 1) if ingreso_usd_c > 0 else 0.0
            costo_por_canal.append(
                {
                    "canal": str(c),
                    "costo_total": round(float(row["importe"]), 2),
                    "ingreso_usd": round(ingreso_usd_c, 2),
                    "margen_pct": margen_c,
                }
            )
        costo_por_canal.sort(key=lambda x: x["margen_pct"], reverse=True)
        if costo_por_canal:
            mejor_canal = str(costo_por_canal[0]["canal"])

    # -----------------------------------------------------------------------
    # Margen por cliente
    # -----------------------------------------------------------------------
    margen_por_cliente = []
    if not df_com.empty and "cliente" in df_com.columns and "margen_estimado" in df_com.columns:
        cli_grp = df_com.copy()
        cli_grp["margen_ponderado"] = cli_grp["margen_estimado"] * cli_grp["importe_usd"]
        cli_grp = (
            cli_grp.groupby("cliente")
            .agg(
                ingreso_usd=("importe_usd", "sum"),
                margen_ponderado=("margen_ponderado", "sum"),
            )
            .reset_index()
        )
        cli_grp["margen_pct"] = cli_grp.apply(
            lambda r: round(safe_div(float(r["margen_ponderado"]), float(r["ingreso_usd"])) * 100, 1),
            axis=1,
        )
        cli_grp = cli_grp.sort_values("margen_pct", ascending=False)
        margen_por_cliente = [
            {
                "cliente": str(row["cliente"]),
                "margen_pct": float(row["margen_pct"]),
                "ingreso_usd": round(float(row["ingreso_usd"]), 2),
            }
            for _, row in cli_grp.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Margen por destino
    # -----------------------------------------------------------------------
    margen_por_destino = []
    if not df_com.empty and "destino" in df_com.columns and "margen_estimado" in df_com.columns:
        dest_grp = df_com.copy()
        dest_grp["margen_ponderado"] = dest_grp["margen_estimado"] * dest_grp["importe_usd"]
        dest_grp = (
            dest_grp.groupby("destino")
            .agg(
                importe_usd=("importe_usd", "sum"),
                margen_ponderado=("margen_ponderado", "sum"),
            )
            .reset_index()
        )
        dest_grp["margen_pct"] = dest_grp.apply(
            lambda r: round(safe_div(float(r["margen_ponderado"]), float(r["importe_usd"])) * 100, 1),
            axis=1,
        )
        dest_grp = dest_grp.sort_values("margen_pct", ascending=False)
        margen_por_destino = [
            {"destino": str(row["destino"]), "margen_pct": float(row["margen_pct"])}
            for _, row in dest_grp.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Tabla (lote-level: sum costs by center, join with comercial income)
    # -----------------------------------------------------------------------
    tabla = []
    if "lote" in df_cos.columns and "finca" in df_cos.columns and "centro_costo" in df_cos.columns:
        # Pivot costs by centro_costo per lote+finca
        pivot = (
            df_cos.groupby(["lote", "finca", "centro_costo"])["importe"]
            .sum()
            .reset_index()
            .pivot_table(index=["lote", "finca"], columns="centro_costo", values="importe", fill_value=0)
            .reset_index()
        )
        pivot.columns.name = None
        # Ensure columns exist
        for col_name in ["Campo", "Empaque", "Logística"]:
            if col_name not in pivot.columns:
                pivot[col_name] = 0.0

        # Comercial income per lote (if finca/lote available in comercial)
        com_lote_grp = pd.DataFrame()
        if not df_com.empty and "finca" in df_com.columns and "lote" in df_com.columns:
            com_lote_grp = (
                df_com.groupby(["lote", "finca"])["importe_usd"].sum().reset_index()
            )

        for _, row in pivot.iterrows():
            c_campo = float(row.get("Campo", 0))
            c_empaque = float(row.get("Empaque", 0))
            c_logistica = float(row.get("Logística", 0))
            c_total = c_campo + c_empaque + c_logistica

            ingreso_lote_usd = 0.0
            if not com_lote_grp.empty:
                mask = (com_lote_grp["lote"] == row["lote"]) & (com_lote_grp["finca"] == row["finca"])
                if mask.any():
                    ingreso_lote_usd = float(com_lote_grp[mask]["importe_usd"].values[0])

            c_total_usd = safe_div(c_total, avg_tc)
            margen_val = ingreso_lote_usd - c_total_usd
            margen_p = round(safe_div(margen_val, ingreso_lote_usd) * 100, 1) if ingreso_lote_usd > 0 else 0.0

            tabla.append(
                {
                    "finca": str(row["finca"]),
                    "lote": str(row["lote"]),
                    "costo_campo": round(c_campo, 2),
                    "costo_empaque": round(c_empaque, 2),
                    "costo_logistica": round(c_logistica, 2),
                    "costo_total": round(c_total, 2),
                    "ingreso_usd": round(ingreso_lote_usd, 2),
                    "margen": round(margen_val, 2),
                    "margen_pct": margen_p,
                }
            )
        tabla.sort(key=lambda x: x["margen_pct"], reverse=True)
        if tabla:
            mejor_lote = str(tabla[0]["lote"])

    # -----------------------------------------------------------------------
    # Insights
    # -----------------------------------------------------------------------
    insights = compute_insights_costos(df_cos, df_com)

    kpis["mejor_lote"] = mejor_lote
    kpis["mejor_canal"] = mejor_canal

    return {
        "kpis": kpis,
        "composicion_costo": composicion_costo,
        "costo_por_finca": costo_por_finca,
        "costo_por_lote": costo_por_lote,
        "costo_por_canal": costo_por_canal,
        "margen_por_cliente": margen_por_cliente,
        "margen_por_destino": margen_por_destino,
        "tabla": tabla,
        "insights": insights,
    }
