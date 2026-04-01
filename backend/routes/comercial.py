"""Comercial (sales) route."""
from typing import Optional

import pandas as pd
from fastapi import APIRouter

from backend.services.loaders import load_comercial
from backend.services.filters import apply_comercial_filters
from backend.services.performance import cache_response
from backend.services.metrics import safe_div, pct, month_label, compute_insights_comercial

router = APIRouter()


@router.get("")
@router.get("/")
@cache_response("comercial.csv", maxsize=192)
def get_comercial(
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    cliente: Optional[str] = None,
    destino: Optional[str] = None,
    canal: Optional[str] = None,
    moneda: Optional[str] = None,
):
    df_raw = load_comercial()
    df = apply_comercial_filters(
        df_raw,
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        cliente=cliente,
        destino=destino,
        canal=canal,
        moneda=moneda,
    )

    empty_kpis = {
        "ventas_netas_usd": 0.0,
        "kg_vendidos": 0.0,
        "precio_promedio_kg_usd": 0.0,
        "margen_comercial_pct": 0.0,
        "pct_exportacion": 0.0,
        "pct_mercado_interno": 0.0,
        "pct_industria": 0.0,
        "ticket_promedio_usd": 0.0,
    }

    if df.empty:
        return {
            "kpis": empty_kpis,
            "ventas_por_cliente": [],
            "ventas_por_destino": [],
            "precio_por_calibre": [],
            "evolucion_ventas": [],
            "top_clientes": [],
            "margen_por_canal": [],
            "tabla": [],
            "insights": ["No hay datos comerciales para el período y filtros seleccionados."],
        }

    # -----------------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------------
    ventas_usd = float(df["importe_usd"].sum())
    kg_vendidos = float(df["kg_vendidos"].sum())
    total_imp = float(df["importe_usd"].sum())

    margen_comercial_pct = 0.0
    if total_imp > 0 and "margen_estimado" in df.columns:
        margen_comercial_pct = round(
            float((df["margen_estimado"] * df["importe_usd"]).sum() / total_imp * 100), 1
        )

    # Destination mix by kg
    kg_total = float(df["kg_vendidos"].sum())
    pct_exp = 0.0
    pct_mi = 0.0
    pct_ind = 0.0
    if kg_total > 0 and "destino" in df.columns:
        dest_kg = df.groupby("destino")["kg_vendidos"].sum()
        pct_exp = round(safe_div(float(dest_kg.get("Exportación", 0)), kg_total) * 100, 1)
        pct_mi = round(safe_div(float(dest_kg.get("Mercado Interno", 0)), kg_total) * 100, 1)
        pct_ind = round(safe_div(float(dest_kg.get("Industria", 0)), kg_total) * 100, 1)

    ticket_promedio = round(safe_div(ventas_usd, len(df)), 2)

    kpis = {
        "ventas_netas_usd": round(ventas_usd, 2),
        "kg_vendidos": round(kg_vendidos, 0),
        "precio_promedio_kg_usd": round(safe_div(ventas_usd, kg_vendidos), 4),
        "margen_comercial_pct": margen_comercial_pct,
        "pct_exportacion": pct_exp,
        "pct_mercado_interno": pct_mi,
        "pct_industria": pct_ind,
        "ticket_promedio_usd": ticket_promedio,
    }

    # -----------------------------------------------------------------------
    # Ventas por cliente
    # -----------------------------------------------------------------------
    ventas_por_cliente = []
    if "cliente" in df.columns:
        cli_grp = (
            df.groupby("cliente")
            .agg(importe_usd=("importe_usd", "sum"), kg=("kg_vendidos", "sum"))
            .reset_index()
            .sort_values("importe_usd", ascending=False)
        )
        ventas_por_cliente = [
            {
                "cliente": str(row["cliente"]),
                "importe_usd": round(float(row["importe_usd"]), 2),
                "kg": round(float(row["kg"]), 0),
            }
            for _, row in cli_grp.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Ventas por destino
    # -----------------------------------------------------------------------
    ventas_por_destino = []
    if "destino" in df.columns:
        total_usd = float(df["importe_usd"].sum())
        dest_grp = (
            df.groupby("destino")["importe_usd"].sum().reset_index().sort_values(
                "importe_usd", ascending=False
            )
        )
        ventas_por_destino = [
            {
                "destino": str(row["destino"]),
                "importe_usd": round(float(row["importe_usd"]), 2),
                "pct": round(safe_div(float(row["importe_usd"]), total_usd) * 100, 1),
            }
            for _, row in dest_grp.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Precio por calibre
    # -----------------------------------------------------------------------
    precio_por_calibre = []
    if "calibre" in df.columns and "precio_unitario_usd" in df.columns:
        cal_grp = (
            df.groupby("calibre")["precio_unitario_usd"]
            .mean()
            .reset_index()
            .sort_values("precio_unitario_usd", ascending=False)
        )
        precio_por_calibre = [
            {
                "calibre": str(row["calibre"]),
                "precio_promedio_usd": round(float(row["precio_unitario_usd"]), 4),
            }
            for _, row in cal_grp.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Evolucion ventas mensual
    # -----------------------------------------------------------------------
    evolucion_ventas = []
    if "fecha" in df.columns:
        mes_grp = (
            df.groupby("mes")
            .agg(importe_usd=("importe_usd", "sum"), kg=("kg_vendidos", "sum"))
            .reset_index()
            .sort_values("mes")
        )
        evolucion_ventas = [
            {
                "mes": str(row["mes"]),
                "importe_usd": round(float(row["importe_usd"]), 2),
                "kg": round(float(row["kg"]), 0),
            }
            for _, row in mes_grp.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Top clientes (top 10 by importe_usd)
    # -----------------------------------------------------------------------
    top_clientes = []
    if "cliente" in df.columns and "margen_estimado" in df.columns:
        cli_mg = df.copy()
        cli_mg["margen_ponderado"] = cli_mg["margen_estimado"] * cli_mg["importe_usd"]
        cli_mg = (
            cli_mg.groupby("cliente")
            .agg(
                importe_usd=("importe_usd", "sum"),
                margen_ponderado=("margen_ponderado", "sum"),
            )
            .reset_index()
            .sort_values("importe_usd", ascending=False)
            .head(10)
        )
        cli_mg["margen_pct"] = cli_mg.apply(
            lambda r: round(safe_div(float(r["margen_ponderado"]), float(r["importe_usd"])) * 100, 1),
            axis=1,
        )
        top_clientes = [
            {
                "cliente": str(row["cliente"]),
                "importe_usd": round(float(row["importe_usd"]), 2),
                "margen_pct": float(row["margen_pct"]),
            }
            for _, row in cli_mg.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Margen por canal
    # -----------------------------------------------------------------------
    margen_por_canal = []
    if "canal" in df.columns and "margen_estimado" in df.columns:
        canal_grp = df.copy()
        canal_grp["margen_ponderado"] = canal_grp["margen_estimado"] * canal_grp["importe_usd"]
        canal_grp = (
            canal_grp.groupby("canal")
            .agg(
                importe_usd=("importe_usd", "sum"),
                margen_ponderado=("margen_ponderado", "sum"),
            )
            .reset_index()
        )
        canal_grp["margen_pct"] = canal_grp.apply(
            lambda r: round(safe_div(float(r["margen_ponderado"]), float(r["importe_usd"])) * 100, 1),
            axis=1,
        )
        canal_grp = canal_grp.sort_values("margen_pct", ascending=False)
        margen_por_canal = [
            {
                "canal": str(row["canal"]),
                "margen_pct": float(row["margen_pct"]),
                "importe_usd": round(float(row["importe_usd"]), 2),
            }
            for _, row in canal_grp.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Tabla (aggregate by cliente + destino)
    # -----------------------------------------------------------------------
    tabla = []
    if "cliente" in df.columns and "destino" in df.columns:
        tab_grp = df.copy()
        tab_grp["margen_ponderado"] = tab_grp["margen_estimado"] * tab_grp["importe_usd"]
        tab_grp = (
            tab_grp.groupby(["cliente", "destino"])
            .agg(
                kg_vendidos=("kg_vendidos", "sum"),
                importe_usd=("importe_usd", "sum"),
                margen_ponderado=("margen_ponderado", "sum"),
                estado_cobro=("estado_cobro", lambda s: s.mode().iloc[0] if not s.mode().empty else ""),
            )
            .reset_index()
            .sort_values("importe_usd", ascending=False)
        )
        tab_grp["precio_promedio"] = tab_grp.apply(
            lambda r: safe_div(float(r["importe_usd"]), float(r["kg_vendidos"])), axis=1
        )
        tab_grp["margen_pct"] = tab_grp.apply(
            lambda r: round(safe_div(float(r["margen_ponderado"]), float(r["importe_usd"])) * 100, 1),
            axis=1,
        )
        tabla = [
            {
                "cliente": str(row["cliente"]),
                "destino": str(row["destino"]),
                "kg_vendidos": round(float(row["kg_vendidos"]), 0),
                "precio_promedio": round(float(row["precio_promedio"]), 4),
                "importe_usd": round(float(row["importe_usd"]), 2),
                "margen_pct": float(row["margen_pct"]),
                "estado_cobro": str(row["estado_cobro"]),
            }
            for _, row in tab_grp.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Insights
    # -----------------------------------------------------------------------
    insights = compute_insights_comercial(df)

    return {
        "kpis": kpis,
        "ventas_por_cliente": ventas_por_cliente,
        "ventas_por_destino": ventas_por_destino,
        "precio_por_calibre": precio_por_calibre,
        "evolucion_ventas": evolucion_ventas,
        "top_clientes": top_clientes,
        "margen_por_canal": margen_por_canal,
        "tabla": tabla,
        "insights": insights,
    }
