import os
import time
import logging
from functools import lru_cache, wraps

import plotly.graph_objects as go
import requests
from dash import html

from frontend.components.empty_state import empty_state, error_state, panel_notice
from frontend.chart_theme import (
    CHART_COLORS,
    add_donut_center_label,
    add_metric_badge,
    add_peak_annotation,
    add_reference_line,
    best_index,
    chart_layout,
    compact_number,
    donut_layout,
    empty_figure,
    error_figure,
    register_plotly_theme,
    smart_bar_colors,
)

API_BASE = os.getenv("LEMON_API_BASE", "http://127.0.0.1:8000").rstrip("/")
REQUEST_CACHE_TTL = 8
REQUEST_CACHE_MAX = 256
_HTTP = requests.Session()
_REQUEST_CACHE: dict[tuple, tuple[float, dict]] = {}
LOGGER = logging.getLogger(__name__)
register_plotly_theme()


def _cache_key(path: str, params=None) -> tuple:
    normalized = tuple(sorted((str(key), str(value)) for key, value in (params or {}).items()))
    return path, normalized


def _prune_request_cache():
    if len(_REQUEST_CACHE) <= REQUEST_CACHE_MAX:
        return
    oldest = sorted(_REQUEST_CACHE.items(), key=lambda item: item[1][0])[: len(_REQUEST_CACHE) - REQUEST_CACHE_MAX]
    for key, _ in oldest:
        _REQUEST_CACHE.pop(key, None)


def api_get(path: str, params=None, timeout: int = 10) -> dict:
    key = _cache_key(path, params)
    now = time.monotonic()
    cached = _REQUEST_CACHE.get(key)
    if cached and now - cached[0] <= REQUEST_CACHE_TTL:
        return cached[1]

    try:
        response = _HTTP.get(f"{API_BASE}{path}", params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        _REQUEST_CACHE[key] = (now, data)
        _prune_request_cache()
        return data
    except requests.Timeout:
        LOGGER.warning("API timeout on %s with params=%s", path, params)
        return {"_request_error": "La fuente de datos demoró demasiado en responder."}
    except requests.RequestException:
        LOGGER.exception("API request failed on %s with params=%s", path, params)
        return {"_request_error": "No se pudo conectar con el backend del panel."}
    except ValueError:
        LOGGER.exception("Invalid API response on %s with params=%s", path, params)
        return {"_request_error": "La respuesta del backend no fue válida."}
    except Exception:
        LOGGER.exception("Unexpected API error on %s with params=%s", path, params)
        return {"_request_error": "Ocurrió un error inesperado al cargar la información."}


@lru_cache(maxsize=64)
def _cached_options(endpoint: str, key: str, all_label: str, all_value: str):
    data = api_get(f"/api/filtros/{endpoint}", timeout=1)
    items = data.get(key, [])
    options = [{"label": all_label, "value": all_value}] + [
        {"label": str(item), "value": str(item)} for item in items
    ]
    return tuple((opt["label"], opt["value"]) for opt in options)


def fetch_options(endpoint: str, key: str, all_label: str = "Todos", all_value: str = "") -> list[dict]:
    return [
        {"label": label, "value": value}
        for label, value in _cached_options(endpoint, key, all_label, all_value)
    ]


def build_options(items: list, all_label: str = "Todos", all_value: str = "") -> list[dict]:
    return [{"label": all_label, "value": all_value}] + [
        {"label": str(item), "value": str(item)} for item in items
    ]


def panel_filter_options(panel: str, **kwargs) -> dict:
    return api_get(f"/api/filtros/panel/{panel}", params=filter_params(**kwargs), timeout=2)


@lru_cache(maxsize=1)
def available_campaigns() -> tuple[str, ...]:
    options = fetch_options("campanas", "campanas")
    return tuple(str(option["value"]) for option in options if option.get("value"))


def sanitize_dropdown_value(value, options: list[dict], fallback: str = ""):
    valid_values = {str(option.get("value", "")) for option in options}
    if value in [None, "", "Todos"]:
        return fallback
    return value if str(value) in valid_values else fallback


def insights_panel(title: str, insights: list[str]) -> html.Div:
    content = insights or ["No hay insights disponibles para la selección actual."]
    return html.Div(
        [
            html.Div(title, className="insights-title"),
            *[html.Div(item, className="insight-item") for item in content],
        ],
        className="insights-panel",
    )


def filter_params(**kwargs) -> dict:
    return {key: (value or "") for key, value in kwargs.items()}


def empty_context_message(campaña: str | None = None) -> str:
    campaigns = available_campaigns()
    if not campaigns:
        return ""
    if len(campaigns) == 1:
        only = campaigns[0]
        if campaña and campaña != only:
            return f"Los datos disponibles comienzan desde la campaña {only}."
        return f"Los datos disponibles comienzan desde la campaña {only}."
    first_campaign = campaigns[0]
    last_campaign = campaigns[-1]
    if campaña:
        return f"Los datos disponibles abarcan campañas {first_campaign} a {last_campaign}. Revisá también el rango de fechas."
    return f"Los datos disponibles abarcan campañas {first_campaign} a {last_campaign}."


def empty_state_actions(path: str) -> list[html.A]:
    return [
        html.A("Limpiar filtros", href=path, className="empty-state-button"),
    ]


def panel_empty_state(
    panel_name: str,
    path: str,
    campaña: str | None = None,
    message: str = "No se registraron datos para los filtros seleccionados",
):
    return empty_state(
        title="No hay datos disponibles",
        message=message,
        context=empty_context_message(campaña),
        actions=empty_state_actions(path),
    )


def safe_callback(fallback_factory, label: str = "callback"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                LOGGER.exception("Frontend callback failed: %s", label)
                return fallback_factory()

        return wrapper

    return decorator


def page_failure_outputs(
    panel_name: str,
    *,
    kpi_blocks: int,
    chart_heights: list[int],
    insights_title: str,
    message: str = "No fue posible actualizar este panel con la selección actual.",
):
    kpi_notice = panel_notice(
        title=f"{panel_name} temporalmente no disponible",
        message=message,
        tone="error",
    )
    kpi_outputs = [kpi_notice] + [html.Div() for _ in range(max(0, kpi_blocks - 1))]
    chart_outputs = [
        error_figure("No se pudo cargar este visual con la información actual.", height=height)
        for height in chart_heights
    ]
    insights_output = insights_panel(
        insights_title,
        ["No fue posible actualizar este panel. Recargá la vista o revisá la conexión con el backend."],
    )
    table_output = error_state(
        title="No se pudo cargar el detalle",
        message="Intentá nuevamente en unos segundos o ajustá los filtros para volver a consultar.",
    )
    return (*kpi_outputs, *chart_outputs, insights_output, table_output)


def page_empty_outputs(
    panel_name: str,
    *,
    path: str,
    kpi_blocks: int,
    chart_heights: list[int],
    insights_title: str,
    campaña: str | None = None,
):
    context_message = empty_context_message(campaña)
    banner = panel_empty_state(panel_name, path=path, campaña=campaña)
    kpi_outputs = [banner] + [html.Div() for _ in range(max(0, kpi_blocks - 1))]
    chart_outputs = [
        empty_figure(
            "No se registraron datos para los filtros seleccionados.",
            height=height,
            context=context_message,
        )
        for height in chart_heights
    ]
    insights_output = insights_panel(
        insights_title,
        ["No hay insights disponibles porque no se registraron datos para la selección actual."],
    )
    table_output = empty_state(
        title="No hay datos disponibles",
        message="No se registraron datos para los filtros seleccionados",
        context=context_message,
        actions=empty_state_actions(path),
    )
    return (*kpi_outputs, *chart_outputs, insights_output, table_output)


def fmt_int(value) -> str:
    return f"{float(value or 0):,.0f}"


def fmt_num(value, digits: int = 1) -> str:
    return f"{float(value or 0):,.{digits}f}"


def fmt_ars(value, digits: int = 0) -> str:
    return f"ARS {float(value or 0):,.{digits}f}"


def fmt_usd(value, digits: int = 0) -> str:
    return f"USD {float(value or 0):,.{digits}f}"


MONTH_LABELS = {
    "01": "Ene",
    "02": "Feb",
    "03": "Mar",
    "04": "Abr",
    "05": "May",
    "06": "Jun",
    "07": "Jul",
    "08": "Ago",
    "09": "Sep",
    "10": "Oct",
    "11": "Nov",
    "12": "Dic",
}


def format_month_label(value: str) -> str:
    raw = str(value or "")
    if len(raw) == 7 and raw[4] == "-":
        return MONTH_LABELS.get(raw[-2:], raw)
    return raw


def format_week_label(value: str) -> str:
    raw = str(value or "")
    if "-W" in raw:
        return f"Sem {raw.split('-W')[-1]}"
    return raw


def format_period_label(value: str) -> str:
    raw = str(value or "")
    if "-W" in raw:
        return format_week_label(raw)
    if len(raw) == 7 and raw[4] == "-":
        return format_month_label(raw)
    return raw
