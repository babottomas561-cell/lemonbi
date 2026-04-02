"""Helpers to build consistent profitability views from commercial data."""
from __future__ import annotations

import pandas as pd

from backend.services.metrics import safe_div


def average_fx(df_com: pd.DataFrame) -> float:
    if df_com.empty or "tipo_cambio" not in df_com.columns:
        return 1.0
    series = pd.to_numeric(df_com["tipo_cambio"], errors="coerce").replace(0, pd.NA).dropna()
    if series.empty:
        return 1.0
    value = float(series.mean())
    return value if value else 1.0


def estimated_margin_summary(df_com: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Aggregate estimated commercial margin by dimension.

    Returns ingreso, costo estimado y margen ponderado para un grupo
    como canal, cliente o destino, usando margen_estimado de comercial.
    """
    if (
        df_com.empty
        or dimension not in df_com.columns
        or "importe_usd" not in df_com.columns
        or "margen_estimado" not in df_com.columns
    ):
        return pd.DataFrame(
            columns=[
                dimension,
                "ingreso_usd",
                "costo_estimado_usd",
                "costo_estimado_ars",
                "margen_usd",
                "margen_pct",
            ]
        )

    avg_tc = average_fx(df_com)
    working = df_com[[dimension, "importe_usd", "margen_estimado"]].copy()
    working["margen_usd"] = working["importe_usd"] * working["margen_estimado"]

    grouped = (
        working.groupby(dimension, dropna=False)[["importe_usd", "margen_usd"]]
        .sum()
        .reset_index()
        .rename(columns={"importe_usd": "ingreso_usd"})
    )
    grouped["costo_estimado_usd"] = grouped["ingreso_usd"] - grouped["margen_usd"]
    grouped["costo_estimado_ars"] = grouped["costo_estimado_usd"] * avg_tc
    grouped["margen_pct"] = grouped.apply(
        lambda row: round(
            safe_div(float(row["margen_usd"]), float(row["ingreso_usd"])) * 100,
            1,
        ),
        axis=1,
    )

    return grouped.sort_values("margen_pct", ascending=False).reset_index(drop=True)
