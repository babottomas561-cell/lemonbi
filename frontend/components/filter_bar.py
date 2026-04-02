from __future__ import annotations

from datetime import date, datetime, timedelta

from dash import ALL, Input, Output, State, callback, ctx, dcc, html
from dash.exceptions import PreventUpdate

from frontend.utils import available_campaigns, fetch_options

SHORTCUT_ITEMS = (
    ("campaign", "Campaña activa"),
    ("30d", "Últimos 30 días"),
    ("90d", "Últimos 90 días"),
    ("all", "Datos disponibles"),
)


def _normalized_campaign(campaña: str | None) -> str:
    campaigns = available_campaigns()
    if campaña and str(campaña) in campaigns:
        return str(campaña)
    if campaigns:
        return campaigns[-1]
    return str(datetime.today().year)


def _campaign_bounds(campaña: str | None) -> tuple[str, str]:
    year = int(_normalized_campaign(campaña))
    return f"{year}-03-01", f"{year}-11-30"


def _data_bounds() -> tuple[str, str]:
    campaigns = available_campaigns()
    if campaigns:
        return _campaign_bounds(campaigns[0])[0], _campaign_bounds(campaigns[-1])[1]
    return _campaign_bounds(None)


def _shortcut_selection(
    shortcut: str,
    campaña: str | None,
    current_start: str | None,
    current_end: str | None,
) -> tuple[str, str, str]:
    active_campaign = _normalized_campaign(campaña)
    campaign_start, campaign_end = _campaign_bounds(active_campaign)
    start_date = date.fromisoformat(campaign_start)
    end_date = date.fromisoformat(campaign_end)

    if shortcut == "campaign":
        return active_campaign, campaign_start, campaign_end
    if shortcut == "30d":
        return active_campaign, max(start_date, end_date - timedelta(days=29)).isoformat(), campaign_end
    if shortcut == "90d":
        return active_campaign, max(start_date, end_date - timedelta(days=89)).isoformat(), campaign_end
    if shortcut == "all":
        full_start, full_end = _data_bounds()
        return "", full_start, full_end
    return active_campaign, current_start or campaign_start, current_end or campaign_end


def _date_picker(component_id: str, value: str, label: str):
    min_date, max_date = _data_bounds()
    return html.Div(
        [
            html.Div(label, className="date-field-label"),
            html.Div(
                dcc.DatePickerSingle(
                    id=component_id,
                    date=value,
                    display_format="DD MMM YYYY",
                    month_format="MMMM YYYY",
                    first_day_of_week=1,
                    show_outside_days=True,
                    number_of_months_shown=1,
                    day_size=36,
                    clearable=False,
                    reopen_calendar_on_clear=False,
                    min_date_allowed=min_date,
                    max_date_allowed=max_date,
                    initial_visible_month=value,
                ),
                className="date-picker-shell",
            ),
        ],
        className="date-field",
    )


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


def campaign_filter(component_id: str, value: str = "", width: str = "110px", all_label: str = "Todas"):
    campaigns = available_campaigns()
    initial_options = [{"label": all_label, "value": ""}]
    initial_options.extend({"label": campaign, "value": campaign} for campaign in campaigns)
    return dropdown_filter("CAMPAÑA", component_id, initial_options, value=value, width=width)


def date_filter(label: str, component_id: str, value: str):
    min_date, max_date = _data_bounds()
    return html.Div(
        [
            html.Div(label, className="filter-label"),
            html.Div(
                dcc.DatePickerSingle(
                    id=component_id,
                    date=value,
                    display_format="DD MMM YYYY",
                    month_format="MMMM YYYY",
                    first_day_of_week=1,
                    show_outside_days=True,
                    number_of_months_shown=1,
                    day_size=36,
                    clearable=False,
                    reopen_calendar_on_clear=False,
                    min_date_allowed=min_date,
                    max_date_allowed=max_date,
                    initial_visible_month=value,
                ),
                className="date-picker-shell",
            ),
        ],
        className="filter-group",
    )


def date_range_filter(id_prefix: str, start_value: str, end_value: str):
    return html.Div(
        [
            html.Div("PERÍODO", className="filter-label"),
            html.Div(
                [
                    _date_picker(f"{id_prefix}-fecha-desde", start_value, "Desde"),
                    _date_picker(f"{id_prefix}-fecha-hasta", end_value, "Hasta"),
                ],
                className="date-range-fields",
            ),
            html.Div(
                [
                    html.Button(
                        label,
                        id={"type": "date-shortcut", "panel": id_prefix, "shortcut": shortcut},
                        n_clicks=0,
                        type="button",
                        className="date-shortcut-button",
                    )
                    for shortcut, label in SHORTCUT_ITEMS
                ],
                className="date-shortcuts",
            ),
        ],
        className="filter-group filter-group-date-range",
    )


def render_filter_bar(filters: list):
    return html.Div(filters, className="filter-bar")


def render_global_filters(id_prefix: str = "global"):
    return render_filter_bar(
        [
            campaign_filter(f"{id_prefix}-campaña", value="2024", width="110px"),
            date_range_filter(id_prefix, "2024-03-01", "2024-11-30"),
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


def bind_date_shortcuts(id_prefix: str):
    @callback(
        Output(f"{id_prefix}-campaña", "value", allow_duplicate=True),
        Output(f"{id_prefix}-fecha-desde", "date"),
        Output(f"{id_prefix}-fecha-hasta", "date"),
        Input({"type": "date-shortcut", "panel": id_prefix, "shortcut": ALL}, "n_clicks"),
        State({"type": "date-shortcut", "panel": id_prefix, "shortcut": ALL}, "id"),
        State(f"{id_prefix}-campaña", "value"),
        State(f"{id_prefix}-fecha-desde", "date"),
        State(f"{id_prefix}-fecha-hasta", "date"),
        prevent_initial_call=True,
    )
    def apply_date_shortcut(_clicks, _ids, campaña, current_start, current_end):
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate
        shortcut = triggered.get("shortcut")
        if not shortcut:
            raise PreventUpdate
        return _shortcut_selection(shortcut, campaña, current_start, current_end)

    @callback(
        Output(f"{id_prefix}-fecha-desde", "date", allow_duplicate=True),
        Output(f"{id_prefix}-fecha-hasta", "date", allow_duplicate=True),
        Input(f"{id_prefix}-campaña", "value"),
        State(f"{id_prefix}-fecha-desde", "date"),
        State(f"{id_prefix}-fecha-hasta", "date"),
        prevent_initial_call=True,
    )
    def sync_dates_with_campaign(campaña, current_start, current_end):
        if not campaña:
            raise PreventUpdate
        campaign_start, campaign_end = _campaign_bounds(campaña)
        if (
            not current_start
            or not current_end
            or current_start[:4] != str(campaña)
            or current_end[:4] != str(campaña)
        ):
            return campaign_start, campaign_end

        if current_start < campaign_start or current_end > campaign_end:
            return campaign_start, campaign_end

        raise PreventUpdate
