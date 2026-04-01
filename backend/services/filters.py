"""Filter functions for each DataFrame. All filters are optional."""
import pandas as pd
from typing import Optional


def apply_date_range(
    df: pd.DataFrame,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    col: str = "fecha",
) -> pd.DataFrame:
    """Filter a DataFrame by a date range on the given column."""
    if df.empty:
        return df
    if fecha_desde and fecha_desde != "Todos":
        try:
            df = df[df[col] >= pd.Timestamp(fecha_desde)]
        except Exception:
            pass
    if fecha_hasta and fecha_hasta != "Todos":
        try:
            df = df[df[col] <= pd.Timestamp(fecha_hasta)]
        except Exception:
            pass
    return df


def _str_filter(df: pd.DataFrame, col: str, value: Optional[str]) -> pd.DataFrame:
    """Apply an equality filter on a string column if value is set and not 'Todos'."""
    if value and value != "Todos" and not df.empty and col in df.columns:
        df = df[df[col] == value]
    return df


def _campaign_filter(df: pd.DataFrame, campaña: Optional[str]) -> pd.DataFrame:
    if campaña and campaña != "Todos" and not df.empty:
        if "campaña_str" in df.columns:
            return df[df["campaña_str"] == str(campaña)]
        return df[df["campaña"].astype(str) == str(campaña)]
    return df


def apply_campo_filters(
    df: pd.DataFrame,
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    finca: Optional[str] = None,
    lote: Optional[str] = None,
    variedad: Optional[str] = None,
    estado: Optional[str] = None,
    encargado: Optional[str] = None,
) -> pd.DataFrame:
    df = apply_date_range(df, fecha_desde, fecha_hasta)
    df = _campaign_filter(df, campaña)
    df = _str_filter(df, "finca", finca)
    df = _str_filter(df, "lote", lote)
    df = _str_filter(df, "variedad", variedad)
    df = _str_filter(df, "estado_cosecha", estado)
    df = _str_filter(df, "encargado", encargado)
    return df


def apply_empaque_filters(
    df: pd.DataFrame,
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    finca: Optional[str] = None,
    lote: Optional[str] = None,
    calibre: Optional[str] = None,
    turno: Optional[str] = None,
    linea: Optional[str] = None,
    calidad: Optional[str] = None,
) -> pd.DataFrame:
    df = apply_date_range(df, fecha_desde, fecha_hasta)
    df = _campaign_filter(df, campaña)
    df = _str_filter(df, "finca", finca)
    df = _str_filter(df, "lote", lote)
    # calibre can be numeric; compare as string
    if calibre and calibre != "Todos" and not df.empty and "calibre" in df.columns:
        df = df[df["calibre"].astype(str) == str(calibre)]
    df = _str_filter(df, "turno", turno)
    df = _str_filter(df, "linea", linea)
    df = _str_filter(df, "calidad", calidad)
    return df


def apply_comercial_filters(
    df: pd.DataFrame,
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    cliente: Optional[str] = None,
    destino: Optional[str] = None,
    canal: Optional[str] = None,
    moneda: Optional[str] = None,
) -> pd.DataFrame:
    df = apply_date_range(df, fecha_desde, fecha_hasta)
    df = _campaign_filter(df, campaña)
    df = _str_filter(df, "cliente", cliente)
    df = _str_filter(df, "destino", destino)
    df = _str_filter(df, "canal", canal)
    df = _str_filter(df, "moneda", moneda)
    return df


def apply_finanzas_filters(
    df: pd.DataFrame,
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    banco_caja: Optional[str] = None,
    estado: Optional[str] = None,
    cliente_proveedor: Optional[str] = None,
    moneda: Optional[str] = None,
    tipo: Optional[str] = None,
    categoria_flujo: Optional[str] = None,
) -> pd.DataFrame:
    df = apply_date_range(df, fecha_desde, fecha_hasta)
    df = _campaign_filter(df, campaña)
    df = _str_filter(df, "banco_caja", banco_caja)
    df = _str_filter(df, "estado", estado)
    df = _str_filter(df, "cliente_proveedor", cliente_proveedor)
    df = _str_filter(df, "moneda", moneda)
    df = _str_filter(df, "tipo", tipo)
    df = _str_filter(df, "categoria_flujo", categoria_flujo)
    return df


def apply_costos_filters(
    df: pd.DataFrame,
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    finca: Optional[str] = None,
    lote: Optional[str] = None,
    centro_costo: Optional[str] = None,
    tipo_costo: Optional[str] = None,
    canal: Optional[str] = None,
) -> pd.DataFrame:
    df = apply_date_range(df, fecha_desde, fecha_hasta)
    df = _campaign_filter(df, campaña)
    df = _str_filter(df, "finca", finca)
    df = _str_filter(df, "lote", lote)
    df = _str_filter(df, "centro_costo", centro_costo)
    df = _str_filter(df, "tipo_costo", tipo_costo)
    df = _str_filter(df, "canal", canal)
    return df


def apply_contexto_filters(
    df: pd.DataFrame,
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> pd.DataFrame:
    df = apply_date_range(df, fecha_desde, fecha_hasta)
    df = _campaign_filter(df, campaña)
    return df
