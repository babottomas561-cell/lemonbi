from fastapi import APIRouter

from backend.services.loaders import (
    load_campo,
    load_comercial,
    load_contexto,
    load_costos,
    load_empaque,
    load_finanzas,
)
from backend.services.filters import (
    apply_campo_filters,
    apply_comercial_filters,
    apply_contexto_filters,
    apply_costos_filters,
    apply_empaque_filters,
    apply_finanzas_filters,
)
from backend.services.performance import cache_response

router = APIRouter()


def _clean_params(params: dict) -> dict:
    return {key: value for key, value in params.items() if value not in [None, "", "Todos"]}


def _unique_values(df, column: str, as_str: bool = False) -> list[str]:
    if df.empty or column not in df.columns:
        return []
    values = df[column].dropna()
    if as_str:
        values = values.astype(str)
    return sorted(values.astype(str).unique().tolist())


def _panel_options(df, apply_fn, filters: dict, fields: dict[str, str], str_fields: set[str] | None = None) -> dict:
    str_fields = str_fields or set()
    response = {}
    for field_name, column in fields.items():
        scoped_filters = {key: value for key, value in filters.items() if key != field_name}
        if field_name == "campaña":
            scoped_filters.pop("fecha_desde", None)
            scoped_filters.pop("fecha_hasta", None)
        scoped_df = apply_fn(df, **_clean_params(scoped_filters))
        response[field_name] = _unique_values(scoped_df, column, as_str=field_name in str_fields)
    return response


@router.get("/campanas")
def get_campanas():
    df = load_campo()
    return {"campanas": sorted(df["campaña"].astype(str).unique().tolist())}


@router.get("/fincas")
def get_fincas():
    df = load_campo()
    return {"fincas": sorted(df["finca"].unique().tolist())}


@router.get("/variedades")
def get_variedades():
    df = load_campo()
    return {"variedades": sorted(df["variedad"].unique().tolist())}


@router.get("/clientes")
def get_clientes():
    df = load_comercial()
    return {"clientes": sorted(df["cliente"].unique().tolist())}


@router.get("/destinos")
def get_destinos():
    df = load_comercial()
    return {"destinos": sorted(df["destino"].unique().tolist())}


@router.get("/lotes")
def get_lotes():
    df = load_campo()
    return {"lotes": sorted(df["lote"].unique().tolist())}


@router.get("/canales")
def get_canales():
    df = load_comercial()
    return {"canales": sorted(df["canal"].unique().tolist())}


@router.get("/calibres")
def get_calibres():
    df = load_empaque()
    return {"calibres": sorted(df["calibre"].astype(str).unique().tolist())}


@router.get("/turnos")
def get_turnos():
    df = load_empaque()
    return {"turnos": sorted(df["turno"].unique().tolist())}


@router.get("/estados")
def get_estados():
    df = load_campo()
    return {"estados": sorted(df["estado_cosecha"].unique().tolist())}


@router.get("/encargados")
def get_encargados():
    df = load_campo()
    return {"encargados": sorted(df["encargado"].unique().tolist())}


@router.get("/lineas")
def get_lineas():
    df = load_empaque()
    return {"lineas": sorted(df["linea"].unique().tolist())}


@router.get("/calidades")
def get_calidades():
    df = load_empaque()
    return {"calidades": sorted(df["calidad"].unique().tolist())}


@router.get("/bancos")
def get_bancos():
    df = load_finanzas()
    return {"bancos": sorted(df["banco_caja"].unique().tolist())}


@router.get("/estados_finanzas")
def get_estados_finanzas():
    df = load_finanzas()
    return {"estados_finanzas": sorted(df["estado"].unique().tolist())}


@router.get("/centros_costo")
def get_centros_costo():
    df = load_costos()
    return {"centros_costo": sorted(df["centro_costo"].unique().tolist())}


@router.get("/tipos_costo")
def get_tipos_costo():
    df = load_costos()
    return {"tipos_costo": sorted(df["tipo_costo"].unique().tolist())}


@router.get("/monedas_comercial")
def get_monedas_comercial():
    df = load_comercial()
    return {"monedas_comercial": sorted(df["moneda"].unique().tolist())}


@router.get("/monedas_finanzas")
def get_monedas_finanzas():
    df = load_finanzas()
    return {"monedas_finanzas": sorted(df["moneda"].unique().tolist())}


@router.get("/panel/{panel}")
@cache_response("campo.csv", "empaque.csv", "comercial.csv", "finanzas.csv", "costos.csv", maxsize=192)
def get_panel_filter_options(
    panel: str,
    campaña: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    finca: str | None = None,
    lote: str | None = None,
    variedad: str | None = None,
    estado: str | None = None,
    encargado: str | None = None,
    calibre: str | None = None,
    turno: str | None = None,
    linea: str | None = None,
    calidad: str | None = None,
    cliente: str | None = None,
    destino: str | None = None,
    canal: str | None = None,
    moneda: str | None = None,
    banco_caja: str | None = None,
    tipo: str | None = None,
    categoria_flujo: str | None = None,
    centro_costo: str | None = None,
    tipo_costo: str | None = None,
):
    panel = (panel or "").lower()

    if panel == "resumen":
        return _panel_options(
            load_campo(),
            apply_campo_filters,
            {
                "campaña": campaña,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "finca": finca,
                "variedad": variedad,
            },
            {"campaña": "campaña", "finca": "finca", "variedad": "variedad"},
            str_fields={"campaña"},
        )

    if panel == "campo":
        return _panel_options(
            load_campo(),
            apply_campo_filters,
            {
                "campaña": campaña,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "finca": finca,
                "lote": lote,
                "variedad": variedad,
                "estado": estado,
                "encargado": encargado,
            },
            {
                "campaña": "campaña",
                "finca": "finca",
                "variedad": "variedad",
                "lote": "lote",
                "estado": "estado_cosecha",
                "encargado": "encargado",
            },
            str_fields={"campaña"},
        )

    if panel == "empaque":
        return _panel_options(
            load_empaque(),
            apply_empaque_filters,
            {
                "campaña": campaña,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "finca": finca,
                "lote": lote,
                "calibre": calibre,
                "turno": turno,
                "linea": linea,
                "calidad": calidad,
            },
            {
                "campaña": "campaña",
                "finca": "finca",
                "lote": "lote",
                "calibre": "calibre",
                "turno": "turno",
                "linea": "linea",
                "calidad": "calidad",
            },
            str_fields={"campaña", "calibre"},
        )

    if panel == "comercial":
        return _panel_options(
            load_comercial(),
            apply_comercial_filters,
            {
                "campaña": campaña,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "cliente": cliente,
                "destino": destino,
                "canal": canal,
                "moneda": moneda,
            },
            {
                "campaña": "campaña",
                "cliente": "cliente",
                "destino": "destino",
                "canal": "canal",
                "moneda": "moneda",
            },
            str_fields={"campaña"},
        )

    if panel == "finanzas":
        return _panel_options(
            load_finanzas(),
            apply_finanzas_filters,
            {
                "campaña": campaña,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "banco_caja": banco_caja,
                "estado": estado,
                "tipo": tipo,
                "categoria_flujo": categoria_flujo,
            },
            {
                "campaña": "campaña",
                "banco_caja": "banco_caja",
                "estado": "estado",
                "tipo": "tipo",
                "categoria_flujo": "categoria_flujo",
            },
            str_fields={"campaña"},
        )

    if panel == "costos":
        return _panel_options(
            load_costos(),
            apply_costos_filters,
            {
                "campaña": campaña,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "finca": finca,
                "lote": lote,
                "centro_costo": centro_costo,
                "tipo_costo": tipo_costo,
                "canal": canal,
            },
            {
                "campaña": "campaña",
                "finca": "finca",
                "lote": "lote",
                "centro_costo": "centro_costo",
                "tipo_costo": "tipo_costo",
                "canal": "canal",
            },
            str_fields={"campaña"},
        )

    if panel == "contexto":
        return _panel_options(
            load_contexto(),
            apply_contexto_filters,
            {
                "campaña": campaña,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
            },
            {"campaña": "campaña"},
            str_fields={"campaña"},
        )

    return {}
