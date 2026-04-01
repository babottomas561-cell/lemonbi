"""Campo (field / harvest) route."""
from typing import Optional

import pandas as pd
from fastapi import APIRouter

from backend.services.loaders import load_campo
from backend.services.filters import apply_campo_filters
from backend.services.performance import cache_response
from backend.services.metrics import safe_div, pct, compute_insights_campo

router = APIRouter()


@router.get("")
@router.get("/")
@cache_response("campo.csv", maxsize=192)
def get_campo(
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    finca: Optional[str] = None,
    lote: Optional[str] = None,
    variedad: Optional[str] = None,
    estado: Optional[str] = None,
    encargado: Optional[str] = None,
):
    df_raw = load_campo()
    df = apply_campo_filters(
        df_raw,
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
        variedad=variedad,
        estado=estado,
        encargado=encargado,
    )

    # Default empty response
    empty_kpis = {
        "ha_activas": 0.0,
        "ton_cosechadas": 0.0,
        "ton_pendientes": 0.0,
        "rinde_promedio_kg_ha": 0.0,
        "costo_promedio_ha": 0.0,
        "costo_kg_cosechado": 0.0,
        "avance_cosecha_pct": 0.0,
    }

    if df.empty:
        return {
            "kpis": empty_kpis,
            "produccion_por_lote": [],
            "rendimiento_por_finca": [],
            "avance_por_finca": [],
            "comparacion_variedades": [],
            "costo_por_lote": [],
            "tabla": [],
            "insights": ["No hay datos de campo para el período y filtros seleccionados."],
        }

    # Use last record per lote for cumulative KPIs
    last = df.sort_values("fecha").groupby(["lote", "finca"], as_index=False).last()

    # -----------------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------------
    # ha_activas: sum unique lote hectareas
    ha_activas = float(last.groupby("lote")["hectareas"].first().sum())

    ton_cosechadas = float(last["kg_cosechados"].sum()) / 1000.0
    ton_pendientes = float(last["kg_pendientes"].sum()) / 1000.0

    # Weighted average rendimiento by hectareas
    total_ha = float(last["hectareas"].sum())
    if total_ha > 0 and "rendimiento_kg_ha" in last.columns:
        rinde_promedio = float(
            (last["rendimiento_kg_ha"] * last["hectareas"]).sum() / total_ha
        )
    else:
        rinde_promedio = 0.0

    costo_promedio_ha = float(last["costo_por_ha"].mean()) if "costo_por_ha" in last.columns else 0.0

    total_kg_cos = float(last["kg_cosechados"].sum())
    total_costo = float(last["costo_total_lote"].sum()) if "costo_total_lote" in last.columns else 0.0
    costo_kg_cosechado = round(safe_div(total_costo, total_kg_cos), 4)

    total_real = float(last["produccion_real_kg"].sum())
    avance_cosecha_pct = round(safe_div(total_kg_cos, total_real) * 100, 1)

    kpis = {
        "ha_activas": round(ha_activas, 1),
        "ton_cosechadas": round(ton_cosechadas, 1),
        "ton_pendientes": round(ton_pendientes, 1),
        "rinde_promedio_kg_ha": round(rinde_promedio, 1),
        "costo_promedio_ha": round(costo_promedio_ha, 0),
        "costo_kg_cosechado": costo_kg_cosechado,
        "avance_cosecha_pct": avance_cosecha_pct,
    }

    # -----------------------------------------------------------------------
    # Produccion por lote
    # -----------------------------------------------------------------------
    prod_lote = (
        last[["lote", "finca", "kg_cosechados", "rendimiento_kg_ha"]]
        .sort_values("kg_cosechados", ascending=False)
    )
    produccion_por_lote = [
        {
            "lote": str(row["lote"]),
            "finca": str(row["finca"]),
            "kg_cosechados": round(float(row["kg_cosechados"]), 0),
            "rendimiento_kg_ha": round(float(row["rendimiento_kg_ha"]), 1),
        }
        for _, row in prod_lote.iterrows()
    ]

    # -----------------------------------------------------------------------
    # Rendimiento por finca (weighted average)
    # -----------------------------------------------------------------------
    finca_grp = last.copy()
    finca_grp["rendimiento_ponderado"] = finca_grp["rendimiento_kg_ha"] * finca_grp["hectareas"]
    finca_grp = (
        finca_grp.groupby("finca")
        .agg(
            rendimiento_ponderado=("rendimiento_ponderado", "sum"),
            hectareas=("hectareas", "sum"),
        )
        .reset_index()
    )
    finca_grp["rendimiento_promedio_kg_ha"] = finca_grp.apply(
        lambda r: safe_div(float(r["rendimiento_ponderado"]), float(r["hectareas"])), axis=1
    )
    finca_grp = finca_grp.sort_values("rendimiento_promedio_kg_ha", ascending=False)
    rendimiento_por_finca = [
        {
            "finca": str(row["finca"]),
            "rendimiento_promedio_kg_ha": round(float(row["rendimiento_promedio_kg_ha"]), 1),
        }
        for _, row in finca_grp.iterrows()
    ]

    # -----------------------------------------------------------------------
    # Avance por finca
    # -----------------------------------------------------------------------
    avance_finca = (
        last.groupby("finca")
        .agg(
            kg_cosechados=("kg_cosechados", "sum"),
            kg_pendientes=("kg_pendientes", "sum"),
            produccion_real_kg=("produccion_real_kg", "sum"),
        )
        .reset_index()
    )
    avance_finca["pct_avance"] = avance_finca.apply(
        lambda r: round(safe_div(r["kg_cosechados"], r["produccion_real_kg"]) * 100, 1), axis=1
    )
    avance_finca = avance_finca.sort_values("pct_avance", ascending=False)
    avance_por_finca = [
        {
            "finca": str(row["finca"]),
            "pct_avance": float(row["pct_avance"]),
            "kg_cosechados": round(float(row["kg_cosechados"]), 0),
            "kg_pendientes": round(float(row["kg_pendientes"]), 0),
        }
        for _, row in avance_finca.iterrows()
    ]

    # -----------------------------------------------------------------------
    # Comparacion variedades
    # -----------------------------------------------------------------------
    comp_var = []
    if "variedad" in last.columns:
        var_grp = last.copy()
        var_grp["rendimiento_ponderado"] = var_grp["rendimiento_kg_ha"] * var_grp["hectareas"]
        var_grp = (
            var_grp.groupby("variedad")
            .agg(
                kg_total=("kg_cosechados", "sum"),
                rendimiento_ponderado=("rendimiento_ponderado", "sum"),
                hectareas=("hectareas", "sum"),
            )
            .reset_index()
            .sort_values("kg_total", ascending=False)
        )
        var_grp["rendimiento_promedio"] = var_grp.apply(
            lambda r: safe_div(float(r["rendimiento_ponderado"]), float(r["hectareas"])), axis=1
        )
        comp_var = [
            {
                "variedad": str(row["variedad"]),
                "kg_total": round(float(row["kg_total"]), 0),
                "rendimiento_promedio": round(float(row["rendimiento_promedio"]), 1),
            }
            for _, row in var_grp.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Costo por lote
    # -----------------------------------------------------------------------
    costo_lote = last[["lote", "finca", "costo_total_lote", "kg_cosechados"]].copy()
    costo_lote["costo_kg"] = costo_lote.apply(
        lambda r: round(safe_div(float(r["costo_total_lote"]), float(r["kg_cosechados"])), 4), axis=1
    )
    costo_lote = costo_lote.sort_values("costo_total_lote", ascending=False)
    costo_por_lote = [
        {
            "lote": str(row["lote"]),
            "finca": str(row["finca"]),
            "costo_total": round(float(row["costo_total_lote"]), 0),
            "costo_kg": float(row["costo_kg"]),
        }
        for _, row in costo_lote.iterrows()
    ]

    # -----------------------------------------------------------------------
    # Tabla (last record per lote)
    # -----------------------------------------------------------------------
    tabla = [
        {
            "finca": str(row["finca"]),
            "lote": str(row["lote"]),
            "variedad": str(row.get("variedad", "")),
            "hectareas": round(float(row["hectareas"]), 1),
            "prod_estimada_kg": round(float(row["produccion_estimada_kg"]), 0),
            "prod_real_kg": round(float(row["produccion_real_kg"]), 0),
            "rendimiento_kg_ha": round(float(row["rendimiento_kg_ha"]), 1),
            "costo_total": round(float(row["costo_total_lote"]), 0),
            "estado": str(row.get("estado_cosecha", "")),
        }
        for _, row in last.iterrows()
    ]

    # -----------------------------------------------------------------------
    # Insights
    # -----------------------------------------------------------------------
    insights = compute_insights_campo(df)

    return {
        "kpis": kpis,
        "produccion_por_lote": produccion_por_lote,
        "rendimiento_por_finca": rendimiento_por_finca,
        "avance_por_finca": avance_por_finca,
        "comparacion_variedades": comp_var,
        "costo_por_lote": costo_por_lote,
        "tabla": tabla,
        "insights": insights,
    }
