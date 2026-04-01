from dash import html

PAGES = [
    {"badge": "RE", "label": "Resumen Ejecutivo", "href": "/"},
    {"badge": "CA", "label": "Campo", "href": "/campo"},
    {"badge": "EM", "label": "Empaque", "href": "/empaque"},
    {"badge": "CO", "label": "Comercial", "href": "/comercial"},
    {"badge": "FI", "label": "Finanzas", "href": "/finanzas"},
    {"badge": "CR", "label": "Costos y Rentabilidad", "href": "/costos"},
    {"badge": "CX", "label": "Contexto Externo", "href": "/contexto"},
]


def render_sidebar(pathname: str = "/", user_name: str = "Tomás", role: str = "Demo local"):
    items = []
    normalized_path = (pathname or "/").rstrip("/") or "/"
    for page in PAGES:
        target = page["href"].rstrip("/") or "/"
        is_active = normalized_path == target
        items.append(
            html.A(
                [
                    html.Span(page["badge"], className="nav-badge"),
                    html.Span(page["label"]),
                ],
                href=page["href"],
                className=f"nav-item {'active' if is_active else ''}",
            )
        )

    return html.Div(
        id="sidebar",
        children=[
            html.Div(className="sidebar-glow"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("LB", className="logo-monogram"),
                            html.Div(
                                [
                                    html.Div("LemonBI", className="logo-title"),
                                    html.Div("Inteligencia de negocios agroindustrial", className="logo-subtitle"),
                                ],
                                className="logo-stack",
                            ),
                        ],
                        className="logo-row",
                    ),
                    html.Div("Tucumán · negocio citrícola integrado", className="logo-kicker"),
                ],
                className="sidebar-logo",
            ),
            html.Div(
                [
                    html.Div("Módulos", className="nav-section-label"),
                    *items,
                ],
                className="sidebar-nav",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(user_name[:1].upper(), className="sidebar-user-avatar"),
                            html.Div(
                                [
                                    html.Div(user_name, className="sidebar-user-name"),
                                    html.Div(role, className="sidebar-user-role"),
                                ]
                            ),
                        ],
                        className="sidebar-user",
                    ),
                    html.A("Cerrar sesión", href="/logout", className="sidebar-logout"),
                ],
                className="sidebar-footer",
            ),
        ],
    )
