"""Finanzas (finance / cash flow) route."""
from typing import Optional
from datetime import datetime

import pandas as pd
from fastapi import APIRouter

from backend.services.loaders import load_finanzas
from backend.services.filters import apply_finanzas_filters
from backend.services.performance import cache_response, limit_records
from backend.services.metrics import safe_div, week_label, month_label, compute_insights_finanzas

router = APIRouter()


@router.get("")
@router.get("/")
@cache_response("finanzas.csv", maxsize=192)
def get_finanzas(
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    banco_caja: Optional[str] = None,
    estado: Optional[str] = None,
    cliente_proveedor: Optional[str] = None,
    moneda: Optional[str] = None,
    tipo: Optional[str] = None,
    categoria_flujo: Optional[str] = None,
):
    df_raw = load_finanzas()
    df = apply_finanzas_filters(
        df_raw,
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        banco_caja=banco_caja,
        estado=estado,
        cliente_proveedor=cliente_proveedor,
        moneda=moneda,
        tipo=tipo,
        categoria_flujo=categoria_flujo,
    )

    empty_kpis = {
        "saldo_caja": 0.0,
        "ingresos_cobrados": 0.0,
        "egresos_pagados": 0.0,
        "flujo_neto": 0.0,
        "cuentas_cobrar": 0.0,
        "cuentas_pagar": 0.0,
        "capital_trabajo": 0.0,
        "necesidad_financiamiento": 0.0,
    }

    empty_aging = [
        {"rango": "0-30 días", "importe": 0.0},
        {"rango": "31-60 días", "importe": 0.0},
        {"rango": "+60 días", "importe": 0.0},
    ]

    if df.empty:
        return {
            "kpis": empty_kpis,
            "flujo_semanal": [],
            "cobros_vs_pagos": [],
            "aging_cobrar": empty_aging,
            "aging_pagar": [a.copy() for a in empty_aging],
            "evolucion_saldo": [],
            "tabla": [],
            "insights": ["No hay datos financieros para el período y filtros seleccionados."],
        }

    # Separate ingresos / egresos
    ing = df[df["tipo"] == "Ingreso"]
    egr = df[df["tipo"] == "Egreso"]

    # -----------------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------------
    ingresos_cobrados = float(ing[ing["estado"] == "Cobrado"]["importe"].sum())
    egresos_pagados = float(egr[egr["estado"] == "Pagado"]["importe"].sum())
    saldo_caja = ingresos_cobrados - egresos_pagados
    flujo_neto = float(ing["importe"].sum()) - float(egr["importe"].sum())

    cuentas_cobrar = float(ing[ing["estado"] != "Cobrado"]["importe"].sum())
    cuentas_pagar = float(egr[egr["estado"] != "Pagado"]["importe"].sum())
    capital_trabajo = cuentas_cobrar - cuentas_pagar
    necesidad_financiamiento = max(0.0, -capital_trabajo)

    kpis = {
        "saldo_caja": round(saldo_caja, 2),
        "ingresos_cobrados": round(ingresos_cobrados, 2),
        "egresos_pagados": round(egresos_pagados, 2),
        "flujo_neto": round(flujo_neto, 2),
        "cuentas_cobrar": round(cuentas_cobrar, 2),
        "cuentas_pagar": round(cuentas_pagar, 2),
        "capital_trabajo": round(capital_trabajo, 2),
        "necesidad_financiamiento": round(necesidad_financiamiento, 2),
    }

    # -----------------------------------------------------------------------
    # Flujo semanal with cumulative saldo
    # -----------------------------------------------------------------------
    flujo_semanal = []
    if "fecha" in df.columns:
        weeks_ing = (
            df[df["tipo"] == "Ingreso"]
            .groupby("semana")["importe"]
            .sum()
            .rename("ingresos")
        )
        weeks_egr = (
            df[df["tipo"] == "Egreso"]
            .groupby("semana")["importe"]
            .sum()
            .rename("egresos")
        )
        wk = pd.concat([weeks_ing, weeks_egr], axis=1).fillna(0).sort_index().reset_index()
        wk.columns = ["semana", "ingresos", "egresos"]
        wk["saldo_neto"] = wk["ingresos"] - wk["egresos"]
        wk["saldo_acumulado"] = wk["saldo_neto"].cumsum()
        flujo_semanal = [
            {
                "semana": str(row["semana"]),
                "ingresos": round(float(row["ingresos"]), 2),
                "egresos": round(float(row["egresos"]), 2),
                "saldo_acumulado": round(float(row["saldo_acumulado"]), 2),
            }
            for _, row in wk.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Cobros vs pagos mensual
    # -----------------------------------------------------------------------
    cobros_vs_pagos = []
    if "fecha" in df.columns:
        mes_ing = (
            df[df["tipo"] == "Ingreso"]
            .groupby("mes")["importe"]
            .sum()
            .rename("cobros")
        )
        mes_egr = (
            df[df["tipo"] == "Egreso"]
            .groupby("mes")["importe"]
            .sum()
            .rename("pagos")
        )
        mes = pd.concat([mes_ing, mes_egr], axis=1).fillna(0).sort_index().reset_index()
        mes.columns = ["mes", "cobros", "pagos"]
        cobros_vs_pagos = [
            {
                "mes": str(row["mes"]),
                "cobros": round(float(row["cobros"]), 2),
                "pagos": round(float(row["pagos"]), 2),
            }
            for _, row in mes.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Aging (based on vencimiento vs today)
    # -----------------------------------------------------------------------
    anchor_date = (
        pd.Timestamp(df["fecha"].max()).normalize()
        if "fecha" in df.columns and not df.empty
        else pd.Timestamp(datetime.today().date())
    )

    def _build_aging(subset: pd.DataFrame) -> list:
        if subset.empty or "vencimiento" not in subset.columns:
            return [
                {"rango": "0-30 días", "importe": 0.0},
                {"rango": "31-60 días", "importe": 0.0},
                {"rango": "+60 días", "importe": 0.0},
            ]
        subset = subset.copy()
        subset["dias"] = (subset["vencimiento"] - anchor_date).dt.days
        r1 = float(subset[subset["dias"].between(-30, 30)]["importe"].sum())
        r2 = float(subset[subset["dias"].between(-60, -31)]["importe"].sum())
        r3 = float(subset[subset["dias"] < -60]["importe"].sum())
        return [
            {"rango": "0-30 días", "importe": round(r1, 2)},
            {"rango": "31-60 días", "importe": round(r2, 2)},
            {"rango": "+60 días", "importe": round(r3, 2)},
        ]

    pending_ing = ing[ing["estado"] != "Cobrado"]
    pending_egr = egr[egr["estado"] != "Pagado"]
    aging_cobrar = _build_aging(pending_ing)
    aging_pagar = _build_aging(pending_egr)

    # -----------------------------------------------------------------------
    # Evolucion saldo (cumulative by date)
    # -----------------------------------------------------------------------
    evolucion_saldo = []
    if "fecha" in df.columns:
        df_ev = df.copy().sort_values("fecha")
        df_ev["signo"] = df_ev["tipo"].map({"Ingreso": 1, "Egreso": -1}).fillna(0)
        df_ev["flujo"] = df_ev["importe"] * df_ev["signo"]
        daily = df_ev.groupby("fecha")["flujo"].sum().cumsum().reset_index()
        daily.columns = ["fecha", "saldo"]
        evolucion_saldo = [
            {
                "fecha": str(row["fecha"].date()) if hasattr(row["fecha"], "date") else str(row["fecha"]),
                "saldo": round(float(row["saldo"]), 2),
            }
            for _, row in daily.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Tabla
    # -----------------------------------------------------------------------
    tabla_df = df.sort_values("fecha", ascending=False).head(120)
    tabla = [
        {
            "fecha": str(row.fecha.date()) if hasattr(row.fecha, "date") else str(row.fecha),
            "concepto": str(getattr(row, "concepto", "")),
            "tipo": str(getattr(row, "tipo", "")),
            "cliente_proveedor": str(getattr(row, "cliente_proveedor", "")),
            "importe": round(float(row.importe), 2),
            "vencimiento": (
                str(row.vencimiento.date())
                if pd.notnull(getattr(row, "vencimiento", None))
                else ""
            ),
            "estado": str(getattr(row, "estado", "")),
            "moneda": str(getattr(row, "moneda", "")),
        }
        for row in tabla_df.itertuples(index=False)
    ]

    # -----------------------------------------------------------------------
    # Insights
    # -----------------------------------------------------------------------
    insights = compute_insights_finanzas(df)

    return {
        "kpis": kpis,
        "flujo_semanal": flujo_semanal,
        "cobros_vs_pagos": cobros_vs_pagos,
        "aging_cobrar": aging_cobrar,
        "aging_pagar": aging_pagar,
        "evolucion_saldo": evolucion_saldo,
        "tabla": limit_records(tabla),
        "insights": insights,
    }
