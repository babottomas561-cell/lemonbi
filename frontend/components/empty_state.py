"""Reusable status components for empty, loading and error states."""
from dash import html


def status_state(
    title="Sin datos",
    message="No hay información disponible para los filtros seleccionados.",
    icon="○",
    tone: str = "empty",
    context: str = "",
    actions=None,
):
    return html.Div(
        className=f"empty-state state-card state-{tone}",
        children=[
            html.Div(icon, className="empty-state-icon"),
            html.Div(title, className="empty-state-title"),
            html.Div(message, className="empty-state-text"),
            html.Div(context, className="empty-state-context") if context else None,
            html.Div(actions, className="empty-state-actions") if actions else None,
        ],
    )


def empty_state(
    title="Sin datos",
    message="No hay información disponible para los filtros seleccionados.",
    icon="○",
    context: str = "",
    actions=None,
):
    return status_state(title=title, message=message, icon=icon, tone="empty", context=context, actions=actions)


def loading_state(
    title="Preparando vista",
    message="Aplicando filtros y actualizando la información del panel.",
    icon="···",
    context: str = "",
):
    return status_state(title=title, message=message, icon=icon, tone="loading", context=context)


def error_state(
    title="No se pudo cargar este bloque",
    message="Intentá nuevamente en unos segundos.",
    icon="!",
    context: str = "",
    actions=None,
):
    return status_state(title=title, message=message, icon=icon, tone="error", context=context, actions=actions)


def panel_notice(
    title="Panel temporalmente no disponible",
    message="No fue posible actualizar este módulo con la información actual.",
    tone: str = "error",
):
    return html.Div(
        [
            html.Div(title, className="panel-notice-title"),
            html.Div(message, className="panel-notice-text"),
        ],
        className=f"panel-notice panel-notice-{tone}",
    )
