import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

from frontend.auth import current_user, register_auth
from frontend.components.drilldown import render_drilldown_modal
from frontend.components.sidebar import render_sidebar
from frontend.drilldown import register_drilldown_callbacks

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder=os.path.join(BASE_DIR, "frontend", "pages"),
    assets_folder=os.path.join(BASE_DIR, "frontend", "assets"),
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="LemonBI",
)
server = app.server
register_auth(server)


app.layout = html.Div(
    id="app-container",
    children=[
        html.Div(className="app-ambient app-ambient-a"),
        html.Div(className="app-ambient app-ambient-b"),
        dcc.Location(id="app-location"),
        html.Div(id="sidebar-shell"),
        html.Div(
            id="main-content",
            children=[
                dcc.Loading(
                    type="default",
                    color="#516C53",
                    children=html.Div(dash.page_container, id="page-shell"),
                )
            ],
        ),
        render_drilldown_modal(),
    ],
)
register_drilldown_callbacks(app)


@app.callback(Output("sidebar-shell", "children"), Input("app-location", "pathname"))
def sync_shell(pathname):
    user = current_user() or {}
    display_name = user.get("display_name", "Tomás")
    role = user.get("role", "Demo local")
    return render_sidebar(pathname or "/", user_name=display_name, role=role)


if __name__ == "__main__":
    debug_mode = os.getenv("LEMON_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8050")),
        debug=debug_mode,
        dev_tools_ui=debug_mode,
        dev_tools_hot_reload=debug_mode,
    )
