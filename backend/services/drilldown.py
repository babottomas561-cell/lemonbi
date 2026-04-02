"""Reusable drill-down builders for KPI and chart detail views."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

import pandas as pd
from fastapi import HTTPException

from backend.services.filters import (
    apply_campo_filters,
    apply_comercial_filters,
    apply_contexto_filters,
    apply_costos_filters,
    apply_empaque_filters,
    apply_finanzas_filters,
)
from backend.services.loaders import (
    load_campo,
    load_comercial,
    load_contexto,
    load_costos,
    load_empaque,
    load_finanzas,
)
from backend.services.metrics import safe_div
from backend.services.performance import cache_response
from backend.services.profitability import estimated_margin_summary

FILTER_LABELS = {
    "campaña": "Campaña",
    "fecha_desde": "Desde",
    "fecha_hasta": "Hasta",
    "finca": "Finca",
    "lote": "Lote",
    "variedad": "Variedad",
    "estado": "Estado",
    "encargado": "Encargado",
    "cliente": "Cliente",
    "destino": "Destino",
    "canal": "Canal",
    "moneda": "Moneda",
    "calibre": "Calibre",
    "turno": "Turno",
    "linea": "Línea",
    "calidad": "Calidad",
    "banco_caja": "Banco / Caja",
    "cliente_proveedor": "Cliente / Proveedor",
    "tipo": "Tipo",
    "categoria_flujo": "Flujo",
    "centro_costo": "Centro",
    "tipo_costo": "Tipo de costo",
}


def _humanize(value: str) -> str:
    text = str(value).replace("_", " ").strip()
    if not text:
        return ""
    return text[:1].upper() + text[1:]


def _active_filters(filters: dict) -> list[dict]:
    return [
        {"label": FILTER_LABELS.get(key, _humanize(key)), "value": str(value)}
        for key, value in filters.items()
        if value not in (None, "", "Todos")
    ]


def _prepare_rows(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    for column in cleaned.columns:
        if pd.api.types.is_datetime64_any_dtype(cleaned[column]):
            cleaned[column] = cleaned[column].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_float_dtype(cleaned[column]):
            cleaned[column] = cleaned[column].round(4)
    return cleaned.where(pd.notnull(cleaned), None)


def _columns(df: pd.DataFrame) -> list[dict]:
    return [{"name": _humanize(column), "id": column} for column in df.columns]


def _payload(
    title: str,
    description: str,
    df: pd.DataFrame,
    filters: dict,
    file_name: str,
) -> dict:
    prepared = _prepare_rows(df)
    return {
        "title": title,
        "description": description,
        "columns": _columns(prepared),
        "rows": prepared.to_dict("records"),
        "record_count": int(len(prepared)),
        "filters": _active_filters(filters),
        "file_name": file_name,
    }


def _filtered_campo(filters: dict) -> pd.DataFrame:
    return apply_campo_filters(
        load_campo(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
        finca=filters.get("finca"),
        lote=filters.get("lote"),
        variedad=filters.get("variedad"),
        estado=filters.get("estado"),
        encargado=filters.get("encargado"),
    )


def _campo_last(filters: dict) -> pd.DataFrame:
    df = _filtered_campo(filters)
    if df.empty:
        return df
    return df.sort_values("fecha").groupby(["lote", "finca"], as_index=False).last()


def _filtered_empaque(filters: dict) -> pd.DataFrame:
    return apply_empaque_filters(
        load_empaque(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
        finca=filters.get("finca"),
        lote=filters.get("lote"),
        calibre=filters.get("calibre"),
        turno=filters.get("turno"),
        linea=filters.get("linea"),
        calidad=filters.get("calidad"),
    )


def _filtered_comercial(filters: dict) -> pd.DataFrame:
    return apply_comercial_filters(
        load_comercial(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
        cliente=filters.get("cliente"),
        destino=filters.get("destino"),
        canal=filters.get("canal"),
        moneda=filters.get("moneda"),
    )


def _filtered_finanzas(filters: dict) -> pd.DataFrame:
    return apply_finanzas_filters(
        load_finanzas(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
        banco_caja=filters.get("banco_caja"),
        estado=filters.get("estado"),
        cliente_proveedor=filters.get("cliente_proveedor"),
        moneda=filters.get("moneda"),
        tipo=filters.get("tipo"),
        categoria_flujo=filters.get("categoria_flujo"),
    )


def _filtered_costos(filters: dict) -> pd.DataFrame:
    return apply_costos_filters(
        load_costos(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
        finca=filters.get("finca"),
        lote=filters.get("lote"),
        centro_costo=filters.get("centro_costo"),
        tipo_costo=filters.get("tipo_costo"),
        canal=filters.get("canal"),
    )


def _filtered_contexto(filters: dict) -> pd.DataFrame:
    return apply_contexto_filters(
        load_contexto(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
    )


def _costos_margin_table(filters: dict) -> pd.DataFrame:
    df_cos = _filtered_costos(filters)
    df_emp = apply_empaque_filters(
        load_empaque(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
        finca=filters.get("finca"),
        lote=filters.get("lote"),
    )
    df_com = apply_comercial_filters(
        load_comercial(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
        canal=filters.get("canal"),
    )
    if df_cos.empty:
        return pd.DataFrame()

    avg_tc = float(df_com["tipo_cambio"].mean()) if not df_com.empty and "tipo_cambio" in df_com.columns else 1.0
    if avg_tc == 0:
        avg_tc = 1.0

    pivot = (
        df_cos.groupby(["lote", "finca", "centro_costo"])["importe"]
        .sum()
        .reset_index()
        .pivot_table(index=["lote", "finca"], columns="centro_costo", values="importe", fill_value=0)
        .reset_index()
    )
    pivot.columns.name = None
    for col_name in ["Campo", "Empaque", "Logística"]:
        if col_name not in pivot.columns:
            pivot[col_name] = 0.0

    ingresos = pd.DataFrame()
    if not df_com.empty and {"lote", "finca"}.issubset(df_com.columns):
        ingresos = df_com.groupby(["lote", "finca"])["importe_usd"].sum().reset_index()

    records = []
    for _, row in pivot.iterrows():
        ingreso_usd = 0.0
        if not ingresos.empty:
            mask = (ingresos["lote"] == row["lote"]) & (ingresos["finca"] == row["finca"])
            if mask.any():
                ingreso_usd = float(ingresos.loc[mask, "importe_usd"].iloc[0])
        costo_campo = float(row.get("Campo", 0))
        costo_empaque = float(row.get("Empaque", 0))
        costo_logistica = float(row.get("Logística", 0))
        costo_total = costo_campo + costo_empaque + costo_logistica
        margen_usd = ingreso_usd - safe_div(costo_total, avg_tc)
        records.append(
            {
                "finca": str(row["finca"]),
                "lote": str(row["lote"]),
                "costo_campo": round(costo_campo, 2),
                "costo_empaque": round(costo_empaque, 2),
                "costo_logistica": round(costo_logistica, 2),
                "costo_total": round(costo_total, 2),
                "ingreso_usd": round(ingreso_usd, 2),
                "margen_usd": round(margen_usd, 2),
                "margen_pct": round(safe_div(margen_usd, ingreso_usd) * 100, 1) if ingreso_usd > 0 else 0.0,
            }
        )
    return pd.DataFrame(records)


def _resumen_detail(kind: str, item: str, filters: dict) -> dict:
    df_emp = apply_empaque_filters(
        load_empaque(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
        finca=filters.get("finca"),
    )
    df_com = apply_comercial_filters(
        load_comercial(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
        cliente=filters.get("cliente"),
        destino=filters.get("destino"),
        canal=filters.get("canal"),
    )
    df_fin = _filtered_finanzas(filters)
    df_cos = apply_costos_filters(
        load_costos(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
        finca=filters.get("finca"),
    )

    if kind == "kpi":
        if item == "fruta_ingresada_kg":
            return _payload(
                "Fruta ingresada",
                "Detalle operativo base utilizado para sumar los kilos ingresados a empaque.",
                df_emp[["fecha", "finca", "lote", "turno", "linea", "calidad", "kg_ingresados"]],
                filters,
                "resumen_fruta_ingresada",
            )
        if item == "kg_procesados":
            detail = df_emp[["fecha", "finca", "lote", "kg_exportables", "kg_industria"]].copy()
            detail["kg_procesados"] = detail["kg_exportables"] + detail["kg_industria"]
            return _payload(
                "Kg procesados",
                "Suma de kilos exportables e industria procesados en el período filtrado.",
                detail,
                filters,
                "resumen_kg_procesados",
            )
        if item == "pct_exportable":
            grouped = (
                df_emp.groupby(["finca", "lote"])[["kg_ingresados", "kg_exportables"]]
                .sum()
                .reset_index()
            )
            grouped["pct_exportable"] = grouped.apply(
                lambda row: round(safe_div(float(row["kg_exportables"]), float(row["kg_ingresados"])) * 100, 1),
                axis=1,
            )
            return _payload(
                "Porcentaje exportable",
                "Rendimiento exportable por finca y lote sobre el volumen ingresado a empaque.",
                grouped.sort_values("pct_exportable", ascending=False),
                filters,
                "resumen_pct_exportable",
            )
        if item == "ventas_netas_usd":
            return _payload(
                "Ventas netas",
                "Operaciones comerciales consideradas para la facturación neta en USD.",
                df_com[
                    [
                        "fecha",
                        "cliente",
                        "destino",
                        "canal",
                        "finca",
                        "lote",
                        "kg_vendidos",
                        "precio_unitario_usd",
                        "importe_usd",
                    ]
                ],
                filters,
                "resumen_ventas_netas",
            )
        if item == "margen_bruto_pct":
            detail = df_com[
                ["fecha", "cliente", "destino", "canal", "finca", "lote", "importe_usd", "margen_estimado"]
            ].copy()
            detail["margen_bruto_usd"] = detail["importe_usd"] * detail["margen_estimado"]
            detail["margen_pct"] = detail["margen_estimado"] * 100
            return _payload(
                "Margen bruto estimado",
                "Detalle comercial ponderado por importe usado para calcular el margen bruto estimado.",
                detail,
                filters,
                "resumen_margen_bruto",
            )
        if item == "caja_proyectada_30d":
            anchor = pd.Timestamp(df_fin["fecha"].max()) if not df_fin.empty else pd.Timestamp(datetime.today().date())
            horizon = anchor + timedelta(days=30)
            subset = df_fin[(df_fin["vencimiento"] >= anchor) & (df_fin["vencimiento"] <= horizon)].copy()
            return _payload(
                "Caja proyectada 30 días",
                "Cobros y pagos con vencimiento dentro de los próximos 30 días desde la fecha ancla del filtro.",
                subset[
                    [
                        "fecha",
                        "vencimiento",
                        "concepto",
                        "tipo",
                        "cliente_proveedor",
                        "estado",
                        "importe",
                        "banco_caja",
                    ]
                ],
                filters,
                "resumen_caja_30d",
            )
        if item == "costo_kg_exportado":
            subset = df_cos[df_cos["centro_costo"].isin(["Campo", "Empaque", "Logística"])].copy()
            return _payload(
                "Costo promedio por kg exportado",
                "Componentes directos de costo considerados para el costo por kilo exportado.",
                subset[
                    [
                        "fecha",
                        "finca",
                        "lote",
                        "centro_costo",
                        "tipo_costo",
                        "canal",
                        "importe",
                    ]
                ],
                filters,
                "resumen_costo_kg_exportado",
            )
        if item == "cumplimiento_pedidos_pct":
            detail = df_com[
                ["fecha", "cliente", "destino", "canal", "estado_pedido", "estado_cobro", "kg_vendidos", "importe_usd"]
            ].copy()
            return _payload(
                "Cumplimiento de pedidos",
                "Detalle de operaciones comerciales con estado de pedido y estado de cobro.",
                detail,
                filters,
                "resumen_cumplimiento_pedidos",
            )

    if kind == "chart":
        if item == "evolucion_fruta":
            grouped = (
                df_emp.groupby("semana")[["kg_ingresados", "kg_exportables", "kg_industria", "kg_descarte"]]
                .sum()
                .reset_index()
                .sort_values("semana")
            )
            return _payload(
                "Evolución de fruta ingresada",
                "Serie semanal base usada para mostrar el ingreso de fruta y sus principales salidas.",
                grouped,
                filters,
                "resumen_evolucion_fruta",
            )
        if item == "mix_destino":
            grouped = (
                df_com.groupby("destino")[["kg_vendidos", "importe_usd"]]
                .sum()
                .reset_index()
                .sort_values("kg_vendidos", ascending=False)
            )
            grouped["pct_volumen"] = grouped.apply(
                lambda row: round(safe_div(float(row["kg_vendidos"]), float(grouped["kg_vendidos"].sum())) * 100, 1),
                axis=1,
            )
            return _payload(
                "Mix de destino",
                "Agregado comercial por destino usado para la distribución del volumen vendido.",
                grouped,
                filters,
                "resumen_mix_destino",
            )
        if item == "evolucion_ventas":
            grouped = (
                df_com.groupby("semana")[["importe_usd", "kg_vendidos"]]
                .sum()
                .reset_index()
                .sort_values("semana")
            )
            return _payload(
                "Evolución de ventas",
                "Serie semanal de ventas netas y kilos vendidos en la selección actual.",
                grouped,
                filters,
                "resumen_evolucion_ventas",
            )
        if item == "margen_por_mes":
            grouped = (
                df_com.assign(margen_bruto_usd=lambda frame: frame["importe_usd"] * frame["margen_estimado"])
                .groupby("mes")[["importe_usd", "margen_bruto_usd"]]
                .sum()
                .reset_index()
                .sort_values("mes")
                .rename(columns={"importe_usd": "ingresos_usd"})
            )
            return _payload(
                "Margen bruto por mes",
                "Ingresos y margen bruto mensual utilizados para la visualización ejecutiva.",
                grouped,
                filters,
                "resumen_margen_mes",
            )

    raise HTTPException(status_code=404, detail="Drill-down no disponible para este elemento.")


def _campo_detail(kind: str, item: str, filters: dict) -> dict:
    if kind != "kpi":
        raise HTTPException(status_code=404, detail="Drill-down no disponible para este elemento.")
    last = _campo_last(filters)
    if item == "ha_activas":
        df = last[["finca", "lote", "variedad", "hectareas", "encargado"]]
        return _payload("Hectáreas activas", "Superficie activa por lote considerada en la campaña filtrada.", df, filters, "campo_hectareas_activas")
    if item == "ton_cosechadas":
        df = last[["finca", "lote", "kg_cosechados", "hectareas", "estado_cosecha"]].copy()
        df["ton_cosechadas"] = (df["kg_cosechados"] / 1000).round(2)
        return _payload("Toneladas cosechadas", "Último avance por lote usado para el total cosechado.", df, filters, "campo_ton_cosechadas")
    if item == "ton_pendientes":
        df = last[["finca", "lote", "kg_pendientes", "produccion_real_kg", "estado_cosecha"]].copy()
        df["ton_pendientes"] = (df["kg_pendientes"] / 1000).round(2)
        return _payload("Toneladas pendientes", "Volumen pendiente por lote al cierre de la selección activa.", df, filters, "campo_ton_pendientes")
    if item == "rinde_promedio_kg_ha":
        df = last[["finca", "lote", "variedad", "hectareas", "rendimiento_kg_ha"]]
        return _payload("Rinde promedio por hectárea", "Rendimiento final por lote ponderado por hectáreas.", df, filters, "campo_rinde_promedio")
    if item == "costo_promedio_ha":
        df = last[["finca", "lote", "hectareas", "costo_por_ha", "costo_total_lote"]]
        return _payload("Costo por hectárea", "Costo operativo por hectárea y costo total de cada lote.", df, filters, "campo_costo_ha")
    if item == "costo_kg_cosechado":
        df = last[["finca", "lote", "kg_cosechados", "costo_total_lote"]].copy()
        df["costo_kg"] = df.apply(
            lambda row: round(safe_div(float(row["costo_total_lote"]), float(row["kg_cosechados"])), 4),
            axis=1,
        )
        return _payload("Costo por kg cosechado", "Costo total por lote dividido por los kilos cosechados al cierre del período.", df, filters, "campo_costo_kg")
    if item == "avance_cosecha_pct":
        df = last[["finca", "lote", "kg_cosechados", "produccion_real_kg", "estado_cosecha"]].copy()
        df["avance_pct"] = df.apply(
            lambda row: round(safe_div(float(row["kg_cosechados"]), float(row["produccion_real_kg"])) * 100, 1),
            axis=1,
        )
        return _payload("Avance de cosecha", "Avance de cosecha por lote respecto de la producción real estimada.", df, filters, "campo_avance_cosecha")
    raise HTTPException(status_code=404, detail="Drill-down no disponible para este KPI.")


def _empaque_detail(kind: str, item: str, filters: dict) -> dict:
    df = _filtered_empaque(filters)
    if kind == "kpi":
        if item in {"kg_ingresados", "kg_exportables", "kg_industria", "kg_descarte"}:
            return _payload(
                _humanize(item),
                "Detalle operativo de empaque usado para el KPI seleccionado.",
                df[["fecha", "finca", "lote", "turno", "linea", "calibre", "kg_ingresados", "kg_exportables", "kg_industria", "kg_descarte"]],
                filters,
                f"empaque_{item}",
            )
        if item in {"pct_exportable", "pct_industria", "pct_descarte"}:
            grouped = (
                df.groupby(["finca", "lote"])[["kg_ingresados", "kg_exportables", "kg_industria", "kg_descarte"]]
                .sum()
                .reset_index()
            )
            grouped["pct_exportable"] = grouped.apply(lambda row: round(safe_div(float(row["kg_exportables"]), float(row["kg_ingresados"])) * 100, 1), axis=1)
            grouped["pct_industria"] = grouped.apply(lambda row: round(safe_div(float(row["kg_industria"]), float(row["kg_ingresados"])) * 100, 1), axis=1)
            grouped["pct_descarte"] = grouped.apply(lambda row: round(safe_div(float(row["kg_descarte"]), float(row["kg_ingresados"])) * 100, 1), axis=1)
            return _payload(
                _humanize(item),
                "Rendimiento por lote sobre la fruta ingresada a empaque.",
                grouped.sort_values("pct_exportable", ascending=False),
                filters,
                f"empaque_{item}",
            )
        if item in {"cajas_producidas", "cajas_hora", "costo_caja"}:
            detail = df[["fecha", "finca", "lote", "turno", "linea", "cajas_producidas", "horas_operativas", "costo_empaque"]].copy()
            detail["cajas_hora"] = detail.apply(
                lambda row: round(safe_div(float(row["cajas_producidas"]), float(row["horas_operativas"])), 2),
                axis=1,
            )
            detail["costo_caja"] = detail.apply(
                lambda row: round(safe_div(float(row["costo_empaque"]), float(row["cajas_producidas"])), 2),
                axis=1,
            )
            return _payload(
                _humanize(item),
                "Detalle operativo y económico base de productividad y costo por caja.",
                detail,
                filters,
                f"empaque_{item}",
            )
    if kind == "chart":
        if item == "flujo_proceso":
            grouped = pd.DataFrame(
                [
                    {"etapa": "Ingreso", "kg": round(float(df["kg_ingresados"].sum()), 0)},
                    {"etapa": "Exportable", "kg": round(float(df["kg_exportables"].sum()), 0)},
                    {"etapa": "Industria", "kg": round(float(df["kg_industria"].sum()), 0)},
                    {"etapa": "Descarte", "kg": round(float(df["kg_descarte"].sum()), 0)},
                ]
            )
            return _payload("Flujo de proceso", "Descomposición del volumen ingresado entre exportable, industria y descarte.", grouped, filters, "empaque_flujo_proceso")
        if item == "rendimiento_por_lote":
            grouped = (
                df.groupby(["lote", "finca"])[["kg_ingresados", "kg_exportables", "kg_industria", "kg_descarte"]]
                .sum()
                .reset_index()
            )
            grouped["pct_exportable"] = grouped.apply(lambda row: round(safe_div(float(row["kg_exportables"]), float(row["kg_ingresados"])) * 100, 1), axis=1)
            grouped["pct_industria"] = grouped.apply(lambda row: round(safe_div(float(row["kg_industria"]), float(row["kg_ingresados"])) * 100, 1), axis=1)
            grouped["pct_descarte"] = grouped.apply(lambda row: round(safe_div(float(row["kg_descarte"]), float(row["kg_ingresados"])) * 100, 1), axis=1)
            return _payload("Rendimiento por lote", "Tabla base del rendimiento exportable, industria y descarte por lote.", grouped.sort_values("pct_exportable", ascending=False), filters, "empaque_rendimiento_lote")
        if item == "rendimiento_por_calibre":
            grouped = (
                df.groupby("calibre")[["kg_ingresados", "kg_exportables"]]
                .sum()
                .reset_index()
                .sort_values("kg_ingresados", ascending=False)
            )
            grouped["pct_exportable"] = grouped.apply(lambda row: round(safe_div(float(row["kg_exportables"]), float(row["kg_ingresados"])) * 100, 1), axis=1)
            return _payload("Rendimiento por calibre", "Volumen y rendimiento exportable agrupado por calibre.", grouped, filters, "empaque_rendimiento_calibre")
        if item == "productividad_turno":
            grouped = (
                df.groupby("turno")[["cajas_producidas", "horas_operativas"]]
                .sum()
                .reset_index()
                .sort_values("cajas_producidas", ascending=False)
            )
            grouped["cajas_hora"] = grouped.apply(lambda row: round(safe_div(float(row["cajas_producidas"]), float(row["horas_operativas"])), 2), axis=1)
            return _payload("Productividad por turno", "Producción horaria consolidada por turno.", grouped, filters, "empaque_productividad_turno")
        if item == "comparacion_fincas":
            grouped = (
                df.groupby("finca")[["kg_ingresados", "kg_exportables"]]
                .sum()
                .reset_index()
                .sort_values("kg_ingresados", ascending=False)
            )
            grouped["pct_exportable"] = grouped.apply(lambda row: round(safe_div(float(row["kg_exportables"]), float(row["kg_ingresados"])) * 100, 1), axis=1)
            return _payload("Comparación entre fincas", "Rendimiento y volumen por finca dentro del proceso de empaque.", grouped, filters, "empaque_comparacion_fincas")
        if item == "descarte_por_semana":
            grouped = (
                df.groupby("semana")[["kg_descarte", "kg_ingresados"]]
                .sum()
                .reset_index()
                .sort_values("semana")
            )
            grouped["pct_descarte"] = grouped.apply(lambda row: round(safe_div(float(row["kg_descarte"]), float(row["kg_ingresados"])) * 100, 1), axis=1)
            return _payload("Descarte por semana", "Serie semanal del descarte y su peso relativo sobre el volumen ingresado.", grouped, filters, "empaque_descarte_semana")
    raise HTTPException(status_code=404, detail="Drill-down no disponible para este elemento.")


def _comercial_detail(kind: str, item: str, filters: dict) -> dict:
    df = _filtered_comercial(filters)
    if kind == "kpi":
        if item in {"ventas_netas_usd", "kg_vendidos", "precio_promedio_kg_usd", "ticket_promedio_usd"}:
            return _payload(
                _humanize(item),
                "Detalle comercial de operaciones base utilizado para los principales KPIs del módulo.",
                df[["fecha", "cliente", "destino", "canal", "finca", "lote", "kg_vendidos", "precio_unitario_usd", "importe_usd", "moneda"]],
                filters,
                f"comercial_{item}",
            )
        if item == "margen_comercial_pct":
            detail = df[["fecha", "cliente", "destino", "canal", "importe_usd", "margen_estimado"]].copy()
            detail["margen_pct"] = detail["margen_estimado"] * 100
            detail["margen_usd"] = detail["importe_usd"] * detail["margen_estimado"]
            return _payload("Margen comercial", "Detalle ponderado de margen comercial por operación.", detail, filters, "comercial_margen")
        if item in {"pct_exportacion", "pct_mercado_interno", "pct_industria"}:
            grouped = (
                df.groupby("destino")[["kg_vendidos", "importe_usd"]]
                .sum()
                .reset_index()
                .sort_values("kg_vendidos", ascending=False)
            )
            grouped["pct_volumen"] = grouped.apply(lambda row: round(safe_div(float(row["kg_vendidos"]), float(grouped["kg_vendidos"].sum())) * 100, 1), axis=1)
            return _payload("Mix por destino", "Distribución del volumen comercial por destino de venta.", grouped, filters, "comercial_mix_destino")
    if kind == "chart":
        if item == "ventas_por_cliente":
            grouped = (
                df.groupby("cliente")[["importe_usd", "kg_vendidos"]]
                .sum()
                .reset_index()
                .sort_values("importe_usd", ascending=False)
            )
            return _payload("Ventas por cliente", "Ventas acumuladas por cliente para la selección actual.", grouped, filters, "comercial_ventas_cliente")
        if item == "ventas_por_destino":
            grouped = (
                df.groupby("destino")[["importe_usd", "kg_vendidos"]]
                .sum()
                .reset_index()
                .sort_values("importe_usd", ascending=False)
            )
            grouped["pct_facturacion"] = grouped.apply(lambda row: round(safe_div(float(row["importe_usd"]), float(grouped["importe_usd"].sum())) * 100, 1), axis=1)
            return _payload("Ventas por destino", "Facturación y volumen agregados por destino comercial.", grouped, filters, "comercial_ventas_destino")
        if item == "precio_por_calibre":
            grouped = (
                df.groupby("calibre")[["precio_unitario_usd", "kg_vendidos"]]
                .agg({"precio_unitario_usd": "mean", "kg_vendidos": "sum"})
                .reset_index()
                .sort_values("precio_unitario_usd", ascending=False)
                .rename(columns={"precio_unitario_usd": "precio_promedio_usd"})
            )
            return _payload("Precio promedio por calibre", "Precio promedio por kilo agrupado por calibre.", grouped, filters, "comercial_precio_calibre")
        if item == "margen_por_canal":
            grouped = df.assign(
                margen_ponderado=lambda frame: frame["margen_estimado"] * frame["importe_usd"]
            ).groupby("canal")[["importe_usd", "margen_ponderado"]].sum().reset_index()
            grouped["margen_pct"] = grouped.apply(lambda row: round(safe_div(float(row["margen_ponderado"]), float(row["importe_usd"])) * 100, 1), axis=1)
            return _payload("Margen por canal", "Ingresos y margen comercial ponderado por canal.", grouped.sort_values("margen_pct", ascending=False), filters, "comercial_margen_canal")
        if item == "top_clientes":
            grouped = df.assign(
                margen_ponderado=lambda frame: frame["margen_estimado"] * frame["importe_usd"]
            ).groupby("cliente")[["importe_usd", "margen_ponderado"]].sum().reset_index()
            grouped["margen_pct"] = grouped.apply(lambda row: round(safe_div(float(row["margen_ponderado"]), float(row["importe_usd"])) * 100, 1), axis=1)
            return _payload("Top clientes", "Clientes líderes por facturación con su margen ponderado.", grouped.sort_values("importe_usd", ascending=False), filters, "comercial_top_clientes")
        if item == "evolucion_ventas":
            grouped = (
                df.groupby("mes")[["importe_usd", "kg_vendidos"]]
                .sum()
                .reset_index()
                .sort_values("mes")
            )
            return _payload("Evolución de ventas", "Serie mensual de facturación y kilos vendidos.", grouped, filters, "comercial_evolucion_ventas")
    raise HTTPException(status_code=404, detail="Drill-down no disponible para este elemento.")


def _finanzas_detail(kind: str, item: str, filters: dict) -> dict:
    df = _filtered_finanzas(filters)
    ingresos = df[df["tipo"] == "Ingreso"].copy()
    egresos = df[df["tipo"] == "Egreso"].copy()

    if kind == "kpi":
        if item == "saldo_caja":
            detail = pd.concat(
                [
                    ingresos[ingresos["estado"] == "Cobrado"].assign(signo=1),
                    egresos[egresos["estado"] == "Pagado"].assign(signo=-1),
                ],
                ignore_index=True,
            )
            detail["flujo_neto"] = detail["importe"] * detail["signo"]
            return _payload("Saldo de caja", "Movimientos efectivamente cobrados y pagados que componen el saldo de caja.", detail[["fecha", "concepto", "tipo", "cliente_proveedor", "importe", "estado", "banco_caja", "flujo_neto"]], filters, "finanzas_saldo_caja")
        if item == "ingresos_cobrados":
            return _payload("Ingresos cobrados", "Cobros efectivamente realizados dentro del período filtrado.", ingresos[ingresos["estado"] == "Cobrado"][["fecha", "concepto", "cliente_proveedor", "importe", "estado", "banco_caja", "categoria_flujo"]], filters, "finanzas_ingresos_cobrados")
        if item == "egresos_pagados":
            return _payload("Egresos pagados", "Pagos efectivamente realizados dentro del período filtrado.", egresos[egresos["estado"] == "Pagado"][["fecha", "concepto", "cliente_proveedor", "importe", "estado", "banco_caja", "categoria_flujo"]], filters, "finanzas_egresos_pagados")
        if item == "flujo_neto":
            detail = df.copy()
            detail["flujo_neto"] = detail["importe"] * detail["tipo"].map({"Ingreso": 1, "Egreso": -1}).fillna(0)
            return _payload("Flujo neto", "Movimientos financieros con signo para calcular el flujo neto del período.", detail[["fecha", "concepto", "tipo", "cliente_proveedor", "importe", "estado", "categoria_flujo", "flujo_neto"]], filters, "finanzas_flujo_neto")
        if item == "cuentas_cobrar":
            return _payload("Cuentas a cobrar", "Ingresos pendientes o vencidos aún no cobrados.", ingresos[ingresos["estado"] != "Cobrado"][["fecha", "vencimiento", "concepto", "cliente_proveedor", "importe", "estado", "banco_caja"]], filters, "finanzas_cuentas_cobrar")
        if item == "cuentas_pagar":
            return _payload("Cuentas a pagar", "Egresos pendientes o vencidos aún no pagados.", egresos[egresos["estado"] != "Pagado"][["fecha", "vencimiento", "concepto", "cliente_proveedor", "importe", "estado", "banco_caja"]], filters, "finanzas_cuentas_pagar")
        if item in {"capital_trabajo", "necesidad_financiamiento"}:
            cobrar = ingresos[ingresos["estado"] != "Cobrado"].assign(signo=1)
            pagar = egresos[egresos["estado"] != "Pagado"].assign(signo=-1)
            detail = pd.concat([cobrar, pagar], ignore_index=True)
            detail["capital_trabajo"] = detail["importe"] * detail["signo"]
            return _payload("Capital de trabajo", "Detalle pendiente de cobro y pago usado para el capital de trabajo y la necesidad de financiamiento.", detail[["fecha", "vencimiento", "concepto", "tipo", "cliente_proveedor", "importe", "estado", "capital_trabajo"]], filters, "finanzas_capital_trabajo")
    if kind == "chart":
        if item == "flujo_semanal":
            grouped = (
                pd.concat(
                    [
                        ingresos.groupby("semana")["importe"].sum().rename("ingresos"),
                        egresos.groupby("semana")["importe"].sum().rename("egresos"),
                    ],
                    axis=1,
                )
                .fillna(0)
                .sort_index()
                .reset_index()
            )
            grouped["saldo_neto"] = grouped["ingresos"] - grouped["egresos"]
            grouped["saldo_acumulado"] = grouped["saldo_neto"].cumsum()
            return _payload("Flujo de caja semanal", "Serie semanal de ingresos, egresos y saldo acumulado.", grouped, filters, "finanzas_flujo_semanal")
        if item == "evolucion_saldo":
            detail = df.copy().sort_values("fecha")
            detail["flujo_neto"] = detail["importe"] * detail["tipo"].map({"Ingreso": 1, "Egreso": -1}).fillna(0)
            detail["saldo_acumulado"] = detail.groupby("fecha")["flujo_neto"].transform("sum")
            grouped = detail.groupby("fecha")[["flujo_neto"]].sum().cumsum().reset_index().rename(columns={"flujo_neto": "saldo"})
            return _payload("Evolución del saldo", "Curva acumulada de saldo por fecha calendario.", grouped, filters, "finanzas_evolucion_saldo")
        if item == "cobros_vs_pagos":
            grouped = (
                pd.concat(
                    [
                        ingresos.groupby("mes")["importe"].sum().rename("cobros"),
                        egresos.groupby("mes")["importe"].sum().rename("pagos"),
                    ],
                    axis=1,
                )
                .fillna(0)
                .sort_index()
                .reset_index()
            )
            return _payload("Cobros vs pagos", "Comparación mensual entre cobros e importes pagados.", grouped, filters, "finanzas_cobros_pagos")
        if item == "aging":
            anchor = pd.Timestamp(df["fecha"].max()).normalize() if not df.empty else pd.Timestamp(datetime.today().date())

            def build_aging(subset: pd.DataFrame, label: str) -> list[dict]:
                if subset.empty:
                    return []
                working = subset.copy()
                working["dias"] = (working["vencimiento"] - anchor).dt.days
                return [
                    {"tipo": label, "rango": "0-30 días", "importe": round(float(working[working["dias"].between(-30, 30)]["importe"].sum()), 2)},
                    {"tipo": label, "rango": "31-60 días", "importe": round(float(working[working["dias"].between(-60, -31)]["importe"].sum()), 2)},
                    {"tipo": label, "rango": "+60 días", "importe": round(float(working[working["dias"] < -60]["importe"].sum()), 2)},
                ]

            aging_df = pd.DataFrame(
                build_aging(ingresos[ingresos["estado"] != "Cobrado"], "A cobrar")
                + build_aging(egresos[egresos["estado"] != "Pagado"], "A pagar")
            )
            return _payload("Aging de cuentas", "Desagregación por antigüedad de cuentas pendientes de cobrar y pagar.", aging_df, filters, "finanzas_aging")
    raise HTTPException(status_code=404, detail="Drill-down no disponible para este elemento.")


def _costos_detail(kind: str, item: str, filters: dict) -> dict:
    df_cos = _filtered_costos(filters)
    df_com = apply_comercial_filters(
        load_comercial(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
        canal=filters.get("canal"),
    )
    df_emp = apply_empaque_filters(
        load_empaque(),
        campaña=filters.get("campaña"),
        fecha_desde=filters.get("fecha_desde"),
        fecha_hasta=filters.get("fecha_hasta"),
        finca=filters.get("finca"),
        lote=filters.get("lote"),
    )

    if kind == "kpi":
        if item == "costo_fruta_kg":
            return _payload("Costo fruta por kg", "Detalle de costos del centro Campo utilizados para el KPI de costo fruta.", df_cos[df_cos["centro_costo"] == "Campo"][["fecha", "finca", "lote", "tipo_costo", "canal", "importe"]], filters, "costos_costo_fruta")
        if item == "costo_empaque_kg":
            return _payload("Costo empaque por kg", "Detalle de costos del centro Empaque utilizados para el KPI de costo de empaque.", df_cos[df_cos["centro_costo"] == "Empaque"][["fecha", "finca", "lote", "tipo_costo", "canal", "importe"]], filters, "costos_costo_empaque")
        if item == "costo_logistica_kg":
            return _payload("Costo logístico por kg", "Detalle de costos del centro Logística usados en el indicador.", df_cos[df_cos["centro_costo"] == "Logística"][["fecha", "finca", "lote", "tipo_costo", "canal", "importe"]], filters, "costos_costo_logistica")
        if item == "costo_total_kg_exportado":
            subset = df_cos[df_cos["centro_costo"].isin(["Campo", "Empaque", "Logística"])].copy()
            subset["kg_exportables_total"] = float(df_emp["kg_exportables"].sum()) if not df_emp.empty else 0.0
            return _payload("Costo total por kg exportado", "Costos directos considerados y referencia de kilos exportables del período.", subset[["fecha", "finca", "lote", "centro_costo", "tipo_costo", "canal", "importe", "kg_exportables_total"]], filters, "costos_costo_total_exportado")
        if item in {"margen_bruto_usd", "margen_bruto_pct", "mejor_lote"}:
            return _payload("Margen por lote", "Tabla base de ingresos y costos directos por lote utilizada para rentabilidad.", _costos_margin_table(filters).sort_values("margen_pct", ascending=False), filters, "costos_margen_lote")
        if item == "mejor_canal":
            grouped = estimated_margin_summary(df_com, "canal").rename(
                columns={"costo_estimado_ars": "costo_total"}
            )
            return _payload(
                "Margen por canal",
                "Margen comercial estimado por canal, consistente con cliente y destino dentro del panel.",
                grouped[["canal", "costo_total", "costo_estimado_usd", "ingreso_usd", "margen_usd", "margen_pct"]].sort_values("margen_pct", ascending=False),
                filters,
                "costos_margen_canal",
            )
    if kind == "chart":
        if item == "composicion_costo":
            grouped = df_cos.groupby("centro_costo")["importe"].sum().reset_index().rename(columns={"centro_costo": "tipo"}).sort_values("importe", ascending=False)
            grouped["pct"] = grouped.apply(lambda row: round(safe_div(float(row["importe"]), float(grouped["importe"].sum())) * 100, 1), axis=1)
            return _payload("Composición del costo", "Participación de cada centro de costo sobre el total del período.", grouped, filters, "costos_composicion")
        if item == "costo_por_finca":
            grouped = df_cos.groupby("finca")["importe"].sum().reset_index().sort_values("importe", ascending=False)
            exportables = df_emp.groupby("finca")["kg_exportables"].sum().reset_index() if not df_emp.empty else pd.DataFrame(columns=["finca", "kg_exportables"])
            grouped = grouped.merge(exportables, on="finca", how="left").fillna(0)
            grouped["costo_kg"] = grouped.apply(lambda row: round(safe_div(float(row["importe"]), float(row["kg_exportables"])), 4), axis=1)
            grouped = grouped.rename(columns={"importe": "costo_total"})
            return _payload("Costo por finca", "Costo total y costo por kilo exportable agrupados por finca.", grouped, filters, "costos_por_finca")
        if item == "costo_por_canal":
            canal_df = estimated_margin_summary(df_com, "canal").rename(
                columns={"costo_estimado_ars": "costo_total"}
            )
            return _payload(
                "Costo por canal",
                "Costo estimado, ingreso y margen comercial por canal con una lógica consistente de rentabilidad.",
                canal_df[["canal", "costo_total", "costo_estimado_usd", "ingreso_usd", "margen_usd", "margen_pct"]],
                filters,
                "costos_por_canal",
            )
        if item == "costo_por_lote":
            grouped = (
                df_cos.groupby(["lote", "finca"])["importe"]
                .sum()
                .reset_index()
                .rename(columns={"importe": "costo_total"})
                .sort_values("costo_total", ascending=False)
            )
            exportables = (
                df_emp.groupby(["lote", "finca"])["kg_exportables"].sum().reset_index()
                if not df_emp.empty
                else pd.DataFrame(columns=["lote", "finca", "kg_exportables"])
            )
            grouped = grouped.merge(exportables, on=["lote", "finca"], how="left").fillna(0)
            grouped["costo_kg"] = grouped.apply(
                lambda row: round(safe_div(float(row["costo_total"]), float(row["kg_exportables"])), 4),
                axis=1,
            )
            return _payload(
                "Costo por lote",
                "Costo total y costo por kilo exportable agrupados por lote.",
                grouped,
                filters,
                "costos_por_lote",
            )
        if item == "margen_por_cliente":
            grouped = estimated_margin_summary(df_com, "cliente")
            return _payload(
                "Margen por cliente",
                "Margen comercial estimado por cliente con el mismo criterio usado en canal y destino.",
                grouped.sort_values("margen_pct", ascending=False),
                filters,
                "costos_margen_cliente",
            )
        if item == "margen_por_destino":
            grouped = estimated_margin_summary(df_com, "destino")
            return _payload(
                "Margen por destino",
                "Margen comercial estimado por destino con el mismo criterio usado en canal y cliente.",
                grouped.sort_values("margen_pct", ascending=False),
                filters,
                "costos_margen_destino",
            )
    raise HTTPException(status_code=404, detail="Drill-down no disponible para este elemento.")


def _contexto_detail(kind: str, item: str, filters: dict) -> dict:
    if kind != "kpi":
        raise HTTPException(status_code=404, detail="Drill-down no disponible para este elemento.")
    df = _filtered_contexto(filters).sort_values("fecha")
    if item == "dolar_actual":
        return _payload("Dólar de referencia", "Serie diaria utilizada para el valor de referencia más reciente.", df[["fecha", "dolar_referencia"]], filters, "contexto_dolar")
    if item == "lluvia_acumulada_mm":
        return _payload("Lluvia acumulada", "Registro diario de precipitaciones del período seleccionado.", df[["fecha", "lluvia_mm", "indice_riesgo_climatico"]], filters, "contexto_lluvia")
    if item == "temp_min_promedio":
        return _payload("Temperatura mínima", "Serie diaria de temperatura mínima para el cálculo del promedio.", df[["fecha", "temperatura_min", "temperatura_max"]], filters, "contexto_temp_min")
    if item == "temp_max_promedio":
        return _payload("Temperatura máxima", "Serie diaria de temperatura máxima para el cálculo del promedio.", df[["fecha", "temperatura_min", "temperatura_max"]], filters, "contexto_temp_max")
    if item == "precio_referencia_actual":
        return _payload("Precio de referencia", "Serie diaria de precio de referencia usada por el módulo externo.", df[["fecha", "precio_referencia_usd"]], filters, "contexto_precio_ref")
    if item == "indice_riesgo_promedio":
        return _payload("Índice de riesgo climático", "Serie diaria del índice de riesgo climático dentro del período activo.", df[["fecha", "indice_riesgo_climatico", "lluvia_mm", "temperatura_min", "temperatura_max"]], filters, "contexto_riesgo")
    raise HTTPException(status_code=404, detail="Drill-down no disponible para este KPI.")


DETAIL_BUILDERS: dict[str, Callable[[str, str, dict], dict]] = {
    "resumen": _resumen_detail,
    "campo": _campo_detail,
    "empaque": _empaque_detail,
    "comercial": _comercial_detail,
    "finanzas": _finanzas_detail,
    "costos": _costos_detail,
    "contexto": _contexto_detail,
}


@cache_response(
    "campo.csv",
    "empaque.csv",
    "comercial.csv",
    "finanzas.csv",
    "costos.csv",
    "contexto.csv",
    maxsize=512,
)
def get_drilldown_payload(
    kind: str,
    panel: str,
    item: str,
    filters_key: tuple[tuple[str, str], ...] = (),
) -> dict:
    builder = DETAIL_BUILDERS.get(panel)
    if builder is None:
        raise HTTPException(status_code=404, detail="Panel no soportado para drill-down.")
    active_filters = {key: value for key, value in filters_key if value not in (None, "", "Todos")}
    return builder(kind, item, active_filters)
