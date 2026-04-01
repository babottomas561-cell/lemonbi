from dash import dcc, html

from frontend.utils import fetch_options


def dropdown_filter(label: str, component_id: str, options: list[dict], value="", width: str = "150px"):
    return html.Div(
        [
            html.Div(label, className="filter-label"),
            dcc.Dropdown(
                id=component_id,
                options=options,
                value=value,
                clearable=True,
                placeholder="Todos",
                style={"minWidth": width, "fontSize": "13px"},
            ),
        ],
        className="filter-group",
    )


def date_filter(label: str, component_id: str, value: str):
    return html.Div(
        [
            html.Div(label, className="filter-label"),
            dcc.DatePickerSingle(
                id=component_id,
                date=value,
                display_format="DD/MM/YY",
            ),
        ],
        className="filter-group",
    )


def render_filter_bar(filters: list):
    return html.Div(filters, className="filter-bar")


def render_global_filters(id_prefix: str = "global"):
    return render_filter_bar(
        [
            dropdown_filter(
                "CAMPAÑA",
                f"{id_prefix}-campaña",
                fetch_options("campanas", "campanas"),
                value="2024",
                width="110px",
            ),
            date_filter("DESDE", f"{id_prefix}-fecha-desde", "2024-03-01"),
            date_filter("HASTA", f"{id_prefix}-fecha-hasta", "2024-11-30"),
            dropdown_filter(
                "FINCA",
                f"{id_prefix}-finca",
                fetch_options("fincas", "fincas"),
                width="170px",
            ),
            dropdown_filter(
                "VARIEDAD",
                f"{id_prefix}-variedad",
                fetch_options("variedades", "variedades"),
                width="140px",
            ),
        ]
    )
