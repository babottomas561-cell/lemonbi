"""Reusable DataTable component."""
from dash import dash_table, html


def render_table(data, columns, table_id, page_size=12, max_rows=80):
    """
    data: list of dicts
    columns: list of {"name": display_name, "id": dict_key, "type": optional}
    """
    if not data:
        return html.Div(
            "Sin datos para mostrar",
            style={"padding": "20px", "color": "#6B7280", "fontSize": "13px"},
        )

    visible_data = data[:max_rows]
    note = None
    if len(data) > max_rows:
        note = html.Div(
            f"Mostrando {max_rows} de {len(data)} filas para mantener fluidez.",
            style={"padding": "0 0 12px", "fontSize": "12px", "color": "#7A8376"},
        )

    return html.Div(
        [
            note,
            dash_table.DataTable(
                id=table_id,
                data=visible_data,
                columns=columns,
                page_size=min(page_size, len(visible_data)),
                page_action="native",
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto", "maxHeight": "540px", "overflowY": "auto"},
                fixed_rows={"headers": True},
                style_header={
                    "backgroundColor": "#F9FAFB",
                    "fontWeight": "600",
                    "fontSize": "11.5px",
                    "color": "#6B7280",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.4px",
                    "border": "none",
                    "borderBottom": "1px solid #E5E7EB",
                    "padding": "10px 14px",
                },
                style_cell={
                    "fontSize": "13px",
                    "color": "#1A1A1A",
                    "border": "none",
                    "borderBottom": "1px solid #F3F4F6",
                    "padding": "10px 14px",
                    "fontFamily": "'Source Sans 3', 'Segoe UI', sans-serif",
                    "whiteSpace": "normal",
                    "maxWidth": "220px",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
                style_data_conditional=[
                    {"if": {"row_index": "odd"}, "backgroundColor": "#FAFBF9"},
                ],
                style_filter={
                    "fontSize": "12px",
                    "backgroundColor": "#F9FAFB",
                    "border": "none",
                    "borderBottom": "1px solid #E5E7EB",
                },
            ),
        ]
    )
