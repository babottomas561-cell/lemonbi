"""Contexto (external context: weather, exchange rate, reference price) route."""
from typing import Optional

import pandas as pd
from fastapi import APIRouter

from backend.services.loaders import load_contexto
from backend.services.filters import apply_contexto_filters
from backend.services.performance import cache_response
from backend.services.metrics import safe_div, week_label

router = APIRouter()


def _contexto_insights(df: pd.DataFrame) -> list:
    """Generate 3-5 contextual insights in Spanish."""
    insights = []
    if df.empty:
        return ["No hay datos de contexto para el período seleccionado."]

    # 1. Exchange rate trend
    if "dolar_referencia" in df.columns:
        dolar_inicio = float(df.sort_values("fecha")["dolar_referencia"].iloc[0])
        dolar_fin = float(df.sort_values("fecha")["dolar_referencia"].iloc[-1])
        variacion = safe_div(dolar_fin - dolar_inicio, dolar_inicio) * 100
        tendencia = "se depreció" if variacion > 0 else "se apreció"
        insights.append(
            f"El tipo de cambio {tendencia} un {abs(variacion):.1f}% durante el período "
            f"(de ${dolar_inicio:.2f} a ${dolar_fin:.2f})."
        )

    # 2. Rainfall
    if "lluvia_mm" in df.columns:
        lluvia_total = float(df["lluvia_mm"].sum())
        insights.append(
            f"La lluvia acumulada en el período fue de {lluvia_total:.1f} mm."
        )

    # 3. Climate risk
    if "indice_riesgo_climatico" in df.columns:
        riesgo_prom = float(df["indice_riesgo_climatico"].mean())
        nivel = "alto" if riesgo_prom > 3 else ("moderado" if riesgo_prom > 1.5 else "bajo")
        insights.append(
            f"El índice de riesgo climático promedio es {riesgo_prom:.2f} ({nivel})."
        )

    # 4. Reference price trend
    if "precio_referencia_usd" in df.columns:
        precio_inicio = float(df.sort_values("fecha")["precio_referencia_usd"].iloc[0])
        precio_fin = float(df.sort_values("fecha")["precio_referencia_usd"].iloc[-1])
        var_p = safe_div(precio_fin - precio_inicio, precio_inicio) * 100
        dir_p = "aumentó" if var_p > 0 else "disminuyó"
        insights.append(
            f"El precio de referencia {dir_p} un {abs(var_p):.1f}% durante el período "
            f"(de USD {precio_inicio:.3f} a USD {precio_fin:.3f}/kg)."
        )

    # 5. Temperature range
    if "temperatura_min" in df.columns and "temperatura_max" in df.columns:
        t_min = float(df["temperatura_min"].mean())
        t_max = float(df["temperatura_max"].mean())
        insights.append(
            f"La temperatura promedio osciló entre {t_min:.1f}°C y {t_max:.1f}°C durante el período."
        )

    return insights[:5]


@router.get("")
@router.get("/")
@cache_response("contexto.csv", maxsize=128)
def get_contexto(
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    df_raw = load_contexto()
    df = apply_contexto_filters(
        df_raw,
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )

    empty_kpis = {
        "dolar_actual": 0.0,
        "lluvia_acumulada_mm": 0.0,
        "temp_min_promedio": 0.0,
        "temp_max_promedio": 0.0,
        "precio_referencia_actual": 0.0,
        "indice_riesgo_promedio": 0.0,
    }

    if df.empty:
        return {
            "kpis": empty_kpis,
            "lluvia_temperatura": [],
            "evolucion_dolar": [],
            "precio_referencia": [],
            "tabla": [],
            "insights": ["No hay datos de contexto para el período y filtros seleccionados."],
        }

    df_sorted = df.sort_values("fecha")

    # -----------------------------------------------------------------------
    # KPIs (use latest available values)
    # -----------------------------------------------------------------------
    last_row = df_sorted.iloc[-1]
    kpis = {
        "dolar_actual": round(float(last_row["dolar_referencia"]), 2),
        "lluvia_acumulada_mm": round(float(df["lluvia_mm"].sum()), 1),
        "temp_min_promedio": round(float(df["temperatura_min"].mean()), 1),
        "temp_max_promedio": round(float(df["temperatura_max"].mean()), 1),
        "precio_referencia_actual": round(float(last_row["precio_referencia_usd"]), 4),
        "indice_riesgo_promedio": round(float(df["indice_riesgo_climatico"].mean()), 2),
    }

    # -----------------------------------------------------------------------
    # Weekly aggregations for charts
    # -----------------------------------------------------------------------
    # lluvia_temperatura: weekly avg
    lluvia_temp_grp = (
        df_sorted.groupby("semana")
        .agg(
            lluvia_mm=("lluvia_mm", "sum"),
            temp_min=("temperatura_min", "mean"),
            temp_max=("temperatura_max", "mean"),
        )
        .reset_index()
        .sort_values("semana")
    )
    lluvia_temperatura = [
        {
            "fecha": str(row["semana"]),
            "lluvia_mm": round(float(row["lluvia_mm"]), 2),
            "temp_min": round(float(row["temp_min"]), 1),
            "temp_max": round(float(row["temp_max"]), 1),
        }
        for _, row in lluvia_temp_grp.iterrows()
    ]

    # evolucion_dolar: weekly avg
    dolar_grp = (
        df_sorted.groupby("semana")["dolar_referencia"]
        .mean()
        .reset_index()
        .sort_values("semana")
    )
    evolucion_dolar = [
        {
            "fecha": str(row["semana"]),
            "dolar": round(float(row["dolar_referencia"]), 2),
        }
        for _, row in dolar_grp.iterrows()
    ]

    # precio_referencia: weekly avg
    precio_grp = (
        df_sorted.groupby("semana")["precio_referencia_usd"]
        .mean()
        .reset_index()
        .sort_values("semana")
    )
    precio_referencia = [
        {
            "fecha": str(row["semana"]),
            "precio_usd": round(float(row["precio_referencia_usd"]), 4),
        }
        for _, row in precio_grp.iterrows()
    ]

    # -----------------------------------------------------------------------
    # Tabla: weekly aggregation
    # -----------------------------------------------------------------------
    tabla_grp = (
        df_sorted.groupby("semana")
        .agg(
            dolar=("dolar_referencia", "mean"),
            lluvia_mm=("lluvia_mm", "sum"),
            temp_min=("temperatura_min", "mean"),
            temp_max=("temperatura_max", "mean"),
            precio_ref_usd=("precio_referencia_usd", "mean"),
            indice_riesgo=("indice_riesgo_climatico", "mean"),
        )
        .reset_index()
        .sort_values("semana")
    )
    tabla = [
        {
            "fecha": str(row["semana"]),
            "dolar": round(float(row["dolar"]), 2),
            "lluvia_mm": round(float(row["lluvia_mm"]), 2),
            "temp_min": round(float(row["temp_min"]), 1),
            "temp_max": round(float(row["temp_max"]), 1),
            "precio_ref_usd": round(float(row["precio_ref_usd"]), 4),
            "indice_riesgo": round(float(row["indice_riesgo"]), 2),
        }
        for _, row in tabla_grp.iterrows()
    ]

    # -----------------------------------------------------------------------
    # Insights
    # -----------------------------------------------------------------------
    insights = _contexto_insights(df)

    return {
        "kpis": kpis,
        "lluvia_temperatura": lluvia_temperatura,
        "evolucion_dolar": evolucion_dolar,
        "precio_referencia": precio_referencia,
        "tabla": tabla,
        "insights": insights,
    }
