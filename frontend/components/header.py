"""Page header component."""
from dash import html


def render_header(title: str, subtitle: str = "", badge: str = ""):
    return html.Div(
        id="page-header",
        children=[
            html.Div(
                [
                    html.Div("Módulo", className="header-kicker"),
                    html.Div(title, className="header-title"),
                    html.Div(subtitle, className="header-subtitle") if subtitle else None,
                ],
                className="header-copy",
            ),
            html.Div(
                [
                    html.Span(badge, className="header-badge") if badge else None,
                    html.Div(
                        [
                            html.Div("T", className="header-user-avatar"),
                            html.Div(
                                [
                                    html.Div("Tomás", className="header-user-name"),
                                    html.Div("Demo local", className="header-user-role"),
                                ],
                                className="header-user-copy",
                            ),
                        ],
                        className="header-user",
                    ),
                    html.A("Cerrar sesión", href="/logout", className="header-logout"),
                ],
                className="header-actions",
            ),
        ],
    )
