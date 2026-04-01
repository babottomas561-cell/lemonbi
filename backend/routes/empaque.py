"""Empaque (packing house) route."""
from typing import Optional

import pandas as pd
from fastapi import APIRouter

from backend.services.loaders import load_empaque
from backend.services.filters import apply_empaque_filters
from backend.services.performance import cache_response
from backend.services.metrics import safe_div, pct, week_label, compute_insights_empaque

router = APIRouter()


@router.get("")
@router.get("/")
@cache_response("empaque.csv", maxsize=192)
def get_empaque(
    campaña: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    finca: Optional[str] = None,
    lote: Optional[str] = None,
    calibre: Optional[str] = None,
    turno: Optional[str] = None,
    linea: Optional[str] = None,
    calidad: Optional[str] = None,
):
    df_raw = load_empaque()
    df = apply_empaque_filters(
        df_raw,
        campaña=campaña,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        finca=finca,
        lote=lote,
        calibre=calibre,
        turno=turno,
        linea=linea,
        calidad=calidad,
    )

    empty_kpis = {
        "kg_ingresados": 0.0,
        "kg_exportables": 0.0,
        "kg_industria": 0.0,
        "kg_descarte": 0.0,
        "pct_exportable": 0.0,
        "pct_industria": 0.0,
        "pct_descarte": 0.0,
        "cajas_producidas": 0.0,
        "cajas_hora": 0.0,
        "costo_caja": 0.0,
    }

    if df.empty:
        return {
            "kpis": empty_kpis,
            "flujo_proceso": [
                {"etapa": "Ingreso", "kg": 0.0},
                {"etapa": "Exportable", "kg": 0.0},
                {"etapa": "Industria", "kg": 0.0},
                {"etapa": "Descarte", "kg": 0.0},
            ],
            "rendimiento_por_lote": [],
            "rendimiento_por_calibre": [],
            "productividad_turno": [],
            "descarte_por_semana": [],
            "comparacion_fincas": [],
            "tabla": [],
            "insights": ["No hay datos de empaque para el período y filtros seleccionados."],
        }

    # -----------------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------------
    kg_ing = float(df["kg_ingresados"].sum())
    kg_exp = float(df["kg_exportables"].sum())
    kg_ind = float(df["kg_industria"].sum())
    kg_des = float(df["kg_descarte"].sum())
    cajas = float(df["cajas_producidas"].sum())
    horas = float(df["horas_operativas"].sum())
    costo_emp = float(df["costo_empaque"].sum()) if "costo_empaque" in df.columns else 0.0

    kpis = {
        "kg_ingresados": round(kg_ing, 0),
        "kg_exportables": round(kg_exp, 0),
        "kg_industria": round(kg_ind, 0),
        "kg_descarte": round(kg_des, 0),
        "pct_exportable": round(safe_div(kg_exp, kg_ing) * 100, 1),
        "pct_industria": round(safe_div(kg_ind, kg_ing) * 100, 1),
        "pct_descarte": round(safe_div(kg_des, kg_ing) * 100, 1),
        "cajas_producidas": round(cajas, 0),
        "cajas_hora": round(safe_div(cajas, horas), 2),
        "costo_caja": round(safe_div(costo_emp, cajas), 2),
    }

    # -----------------------------------------------------------------------
    # Flujo proceso
    # -----------------------------------------------------------------------
    flujo_proceso = [
        {"etapa": "Ingreso", "kg": round(kg_ing, 0)},
        {"etapa": "Exportable", "kg": round(kg_exp, 0)},
        {"etapa": "Industria", "kg": round(kg_ind, 0)},
        {"etapa": "Descarte", "kg": round(kg_des, 0)},
    ]

    # -----------------------------------------------------------------------
    # Rendimiento por lote
    # -----------------------------------------------------------------------
    rend_lote = []
    if "lote" in df.columns and "finca" in df.columns:
        lote_grp = (
            df.groupby(["lote", "finca"])[
                ["kg_ingresados", "kg_exportables", "kg_industria", "kg_descarte"]
            ]
            .sum()
            .reset_index()
        )
        for _, row in lote_grp.iterrows():
            ing = float(row["kg_ingresados"])
            rend_lote.append(
                {
                    "lote": str(row["lote"]),
                    "finca": str(row["finca"]),
                    "pct_exportable": round(safe_div(float(row["kg_exportables"]), ing) * 100, 1),
                    "pct_industria": round(safe_div(float(row["kg_industria"]), ing) * 100, 1),
                    "pct_descarte": round(safe_div(float(row["kg_descarte"]), ing) * 100, 1),
                }
            )
        rend_lote.sort(key=lambda x: x["pct_exportable"], reverse=True)

    # -----------------------------------------------------------------------
    # Rendimiento por calibre
    # -----------------------------------------------------------------------
    rend_calibre = []
    if "calibre" in df.columns:
        cal_grp = (
            df.groupby("calibre")[["kg_ingresados", "kg_exportables"]]
            .sum()
            .reset_index()
        )
        for _, row in cal_grp.iterrows():
            ing = float(row["kg_ingresados"])
            rend_calibre.append(
                {
                    "calibre": str(row["calibre"]),
                    "pct_exportable": round(safe_div(float(row["kg_exportables"]), ing) * 100, 1),
                    "kg_total": round(ing, 0),
                }
            )
        rend_calibre.sort(key=lambda x: x["pct_exportable"], reverse=True)

    # -----------------------------------------------------------------------
    # Productividad por turno
    # -----------------------------------------------------------------------
    productividad_turno = []
    if "turno" in df.columns:
        turno_grp = (
            df.groupby("turno")[["cajas_producidas", "horas_operativas"]].sum().reset_index()
        )
        for _, row in turno_grp.iterrows():
            h = float(row["horas_operativas"])
            productividad_turno.append(
                {
                    "turno": str(row["turno"]),
                    "cajas_hora": round(safe_div(float(row["cajas_producidas"]), h), 2),
                    "horas_totales": round(h, 1),
                }
            )
        productividad_turno.sort(key=lambda x: x["cajas_hora"], reverse=True)

    # -----------------------------------------------------------------------
    # Descarte por semana
    # -----------------------------------------------------------------------
    descarte_por_semana = []
    if "fecha" in df.columns:
        wk_desc = (
            df.groupby("semana")["kg_descarte"].sum().reset_index().sort_values("semana")
        )
        descarte_por_semana = [
            {"semana": str(row["semana"]), "kg_descarte": round(float(row["kg_descarte"]), 0)}
            for _, row in wk_desc.iterrows()
        ]

    # -----------------------------------------------------------------------
    # Comparacion fincas
    # -----------------------------------------------------------------------
    comparacion_fincas = []
    if "finca" in df.columns:
        finca_grp = (
            df.groupby("finca")[["kg_ingresados", "kg_exportables"]].sum().reset_index()
        )
        for _, row in finca_grp.iterrows():
            ing = float(row["kg_ingresados"])
            comparacion_fincas.append(
                {
                    "finca": str(row["finca"]),
                    "pct_exportable": round(safe_div(float(row["kg_exportables"]), ing) * 100, 1),
                    "kg_ingresados": round(ing, 0),
                }
            )
        comparacion_fincas.sort(key=lambda x: x["pct_exportable"], reverse=True)

    # -----------------------------------------------------------------------
    # Tabla (group by lote + finca)
    # -----------------------------------------------------------------------
    tabla = []
    if "lote" in df.columns and "finca" in df.columns:
        grp = (
            df.groupby(["lote", "finca"])
            .agg(
                kg_ingresados=("kg_ingresados", "sum"),
                kg_exportables=("kg_exportables", "sum"),
                kg_industria=("kg_industria", "sum"),
                kg_descarte=("kg_descarte", "sum"),
            )
            .reset_index()
        )
        # Mode of calibre and calidad per lote+finca
        cal_mode = (
            df.groupby(["lote", "finca"])["calibre"]
            .agg(lambda x: x.mode()[0] if not x.empty else "")
            .reset_index()
            .rename(columns={"calibre": "calibre_dominante"})
        )
        calidad_mode = (
            df.groupby(["lote", "finca"])["calidad"]
            .agg(lambda x: x.mode()[0] if not x.empty else "")
            .reset_index()
            .rename(columns={"calidad": "calidad_dominante"})
        ) if "calidad" in df.columns else pd.DataFrame()

        grp = grp.merge(cal_mode, on=["lote", "finca"], how="left")
        if not calidad_mode.empty:
            grp = grp.merge(calidad_mode, on=["lote", "finca"], how="left")
        else:
            grp["calidad_dominante"] = ""

        for _, row in grp.iterrows():
            ing = float(row["kg_ingresados"])
            tabla.append(
                {
                    "lote": str(row["lote"]),
                    "finca": str(row["finca"]),
                    "kg_ingresados": round(ing, 0),
                    "kg_exportables": round(float(row["kg_exportables"]), 0),
                    "kg_industria": round(float(row["kg_industria"]), 0),
                    "kg_descarte": round(float(row["kg_descarte"]), 0),
                    "pct_exportable": round(safe_div(float(row["kg_exportables"]), ing) * 100, 1),
                    "calibre_dominante": str(row.get("calibre_dominante", "")),
                    "calidad_dominante": str(row.get("calidad_dominante", "")),
                }
            )

    # -----------------------------------------------------------------------
    # Insights
    # -----------------------------------------------------------------------
    insights = compute_insights_empaque(df)

    return {
        "kpis": kpis,
        "flujo_proceso": flujo_proceso,
        "rendimiento_por_lote": rend_lote,
        "rendimiento_por_calibre": rend_calibre,
        "productividad_turno": productividad_turno,
        "descarte_por_semana": descarte_por_semana,
        "comparacion_fincas": comparacion_fincas,
        "tabla": tabla,
        "insights": insights,
    }
