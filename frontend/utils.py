import os
import time
from functools import lru_cache

import plotly.graph_objects as go
import requests
from dash import html

API_BASE = os.getenv("LEMON_API_BASE", "http://127.0.0.1:8000").rstrip("/")
CHART_COLORS = ["#3F6B4B", "#6C8C5A", "#B69245", "#D8C9A5", "#95B29E", "#C26A45", "#78856A"]
REQUEST_CACHE_TTL = 8
REQUEST_CACHE_MAX = 256
_HTTP = requests.Session()
_REQUEST_CACHE: dict[tuple, tuple[float, dict]] = {}


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
    except Exception:
        return {}


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


def sanitize_dropdown_value(value, options: list[dict], fallback: str = ""):
    valid_values = {str(option.get("value", "")) for option in options}
    if value in [None, "", "Todos"]:
        return fallback
    return value if str(value) in valid_values else fallback


def chart_layout(title: str = "", height: int = 320) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=13, color="#243126", family="Manrope")),
        height=height,
        margin=dict(l=36, r=18, t=42, b=36),
        plot_bgcolor="#FFFCF7",
        paper_bgcolor="#FFFCF7",
        font=dict(family="Manrope, Segoe UI, sans-serif", size=12, color="#5E675E"),
        xaxis=dict(showgrid=False, showline=True, linecolor="#E7E1D4", tickangle=-45, automargin=True),
        yaxis=dict(gridcolor="#EEE8DD", showline=False, zeroline=False, automargin=True),
        showlegend=True,
        legend=dict(font=dict(size=11), orientation="h", y=-0.18),
        colorway=CHART_COLORS,
    )


def empty_figure(message: str = "Sin datos para estos filtros") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=13, color="#7A8376", family="Manrope"),
    )
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="#FFFCF7",
        plot_bgcolor="#FFFCF7",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


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


def fmt_int(value) -> str:
    return f"{float(value or 0):,.0f}"


def fmt_num(value, digits: int = 1) -> str:
    return f"{float(value or 0):,.{digits}f}"


def fmt_ars(value, digits: int = 0) -> str:
    return f"ARS {float(value or 0):,.{digits}f}"


def fmt_usd(value, digits: int = 0) -> str:
    return f"USD {float(value or 0):,.{digits}f}"
