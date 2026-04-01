"""Metric helpers and business-insight generators."""
from __future__ import annotations

import pandas as pd
from typing import List


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------

def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Return numerator / denominator, or default when denominator is zero."""
    try:
        if denominator == 0 or pd.isna(denominator):
            return default
        return numerator / denominator
    except Exception:
        return default


def pct(part: float, total: float) -> float:
    """Return percentage rounded to 1 decimal, 0.0 when total is zero."""
    return round(safe_div(part, total, 0.0) * 100, 1)


def fmt_k(val) -> float:
    """Return numeric value as a plain Python float."""
    try:
        return float(val)
    except Exception:
        return 0.0


def week_label(fecha) -> str:
    """Return 'YYYY-WXX' string from a date-like value."""
    try:
        ts = pd.Timestamp(fecha)
        return f"{ts.year}-W{ts.isocalendar()[1]:02d}"
    except Exception:
        return ""


def month_label(fecha) -> str:
    """Return 'YYYY-MM' string from a date-like value."""
    try:
        ts = pd.Timestamp(fecha)
        return f"{ts.year}-{ts.month:02d}"
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Insight generators
# ---------------------------------------------------------------------------

def compute_insights_campo(df_campo_filtered: pd.DataFrame) -> List[str]:
    """Return 3-5 business insights in Spanish from the filtered campo DataFrame."""
    insights: List[str] = []
    if df_campo_filtered.empty:
        return ["No hay datos de campo para el período seleccionado."]

    # Use last record per lote for cumulative KPIs
    last = df_campo_filtered.sort_values("fecha").groupby("lote", as_index=False).last()

    # 1. Lote with best yield
    if not last.empty and "rendimiento_kg_ha" in last.columns:
        best = last.loc[last["rendimiento_kg_ha"].idxmax()]
        insights.append(
            f"El lote {best['lote']} ({best['finca']}) lidera con un rendimiento de "
            f"{best['rendimiento_kg_ha']:,.0f} kg/ha."
        )

    # 2. Lote with worst yield
    if len(last) > 1 and "rendimiento_kg_ha" in last.columns:
        worst = last.loc[last["rendimiento_kg_ha"].idxmin()]
        insights.append(
            f"El lote con menor rendimiento es {worst['lote']} ({worst['finca']}) "
            f"con {worst['rendimiento_kg_ha']:,.0f} kg/ha."
        )

    # 3. Overall harvest progress
    total_real = last["produccion_real_kg"].sum()
    total_cosechado = last["kg_cosechados"].sum()
    if total_real > 0:
        avance = pct(total_cosechado, total_real)
        insights.append(
            f"El avance global de cosecha es del {avance}% "
            f"({total_cosechado / 1_000:,.1f} t cosechadas de {total_real / 1_000:,.1f} t estimadas)."
        )

    # 4. Highest cost per ha finca
    if "finca" in last.columns and "costo_por_ha" in last.columns:
        finca_costo = last.groupby("finca")["costo_por_ha"].mean()
        if not finca_costo.empty:
            top_finca = finca_costo.idxmax()
            insights.append(
                f"La finca {top_finca} tiene el mayor costo promedio por hectárea: "
                f"${finca_costo[top_finca]:,.0f}."
            )

    # 5. Variety comparison
    if "variedad" in last.columns and "kg_cosechados" in last.columns:
        var_kg = last.groupby("variedad")["kg_cosechados"].sum().sort_values(ascending=False)
        if not var_kg.empty:
            top_var = var_kg.index[0]
            insights.append(
                f"La variedad {top_var} representa la mayor producción cosechada "
                f"con {var_kg[top_var] / 1_000:,.1f} t."
            )

    return insights[:5] if insights else ["No se encontraron insights para el período seleccionado."]


def compute_insights_empaque(df_emp_filtered: pd.DataFrame) -> List[str]:
    """Return 3-5 business insights in Spanish from the filtered empaque DataFrame."""
    insights: List[str] = []
    if df_emp_filtered.empty:
        return ["No hay datos de empaque para el período seleccionado."]

    total_ing = df_emp_filtered["kg_ingresados"].sum()
    total_exp = df_emp_filtered["kg_exportables"].sum()
    total_desc = df_emp_filtered["kg_descarte"].sum()

    # 1. Overall exportable rate
    if total_ing > 0:
        pct_exp = pct(total_exp, total_ing)
        insights.append(
            f"El rendimiento exportable global es del {pct_exp}% "
            f"({total_exp / 1_000:,.1f} t exportables de {total_ing / 1_000:,.1f} t ingresadas)."
        )

    # 2. Lote with lowest exportable pct
    if "lote" in df_emp_filtered.columns:
        lote_grp = (
            df_emp_filtered.groupby("lote")[["kg_ingresados", "kg_exportables"]]
            .sum()
            .reset_index()
        )
        lote_grp = lote_grp[lote_grp["kg_ingresados"] > 0]
        if not lote_grp.empty:
            lote_grp["pct_exp"] = lote_grp["kg_exportables"] / lote_grp["kg_ingresados"] * 100
            worst = lote_grp.loc[lote_grp["pct_exp"].idxmin()]
            insights.append(
                f"El lote {worst['lote']} tiene el menor rendimiento exportable con un "
                f"{worst['pct_exp']:.1f}%."
            )

    # 3. Shift with best cajas/hora
    if "turno" in df_emp_filtered.columns:
        turno_grp = (
            df_emp_filtered.groupby("turno")[["cajas_producidas", "horas_operativas"]]
            .sum()
            .reset_index()
        )
        turno_grp = turno_grp[turno_grp["horas_operativas"] > 0]
        if not turno_grp.empty:
            turno_grp["cajas_hora"] = turno_grp["cajas_producidas"] / turno_grp["horas_operativas"]
            best = turno_grp.loc[turno_grp["cajas_hora"].idxmax()]
            insights.append(
                f"El turno {best['turno']} es el más productivo con "
                f"{best['cajas_hora']:.1f} cajas/hora."
            )

    # 4. Calibre with best exportable rate
    if "calibre" in df_emp_filtered.columns:
        cal_grp = (
            df_emp_filtered.groupby("calibre")[["kg_ingresados", "kg_exportables"]]
            .sum()
            .reset_index()
        )
        cal_grp = cal_grp[cal_grp["kg_ingresados"] > 0]
        if not cal_grp.empty:
            cal_grp["pct_exp"] = cal_grp["kg_exportables"] / cal_grp["kg_ingresados"] * 100
            best_cal = cal_grp.loc[cal_grp["pct_exp"].idxmax()]
            insights.append(
                f"El calibre {best_cal['calibre']} presenta el mejor rendimiento exportable: "
                f"{best_cal['pct_exp']:.1f}%."
            )

    # 5. Descarte alert
    if total_ing > 0:
        pct_desc = pct(total_desc, total_ing)
        if pct_desc > 10:
            insights.append(
                f"El descarte representa el {pct_desc}% del ingreso total — "
                f"por encima del umbral recomendado del 10%."
            )
        else:
            insights.append(
                f"El descarte se mantiene bajo control en el {pct_desc}% del ingreso total."
            )

    return insights[:5] if insights else ["No se encontraron insights para el período seleccionado."]


def compute_insights_comercial(df_com_filtered: pd.DataFrame) -> List[str]:
    """Return 3-5 business insights in Spanish from the filtered comercial DataFrame."""
    insights: List[str] = []
    if df_com_filtered.empty:
        return ["No hay datos comerciales para el período seleccionado."]

    # 1. Top client by sales
    if "cliente" in df_com_filtered.columns and "importe_usd" in df_com_filtered.columns:
        cli_grp = df_com_filtered.groupby("cliente")["importe_usd"].sum().sort_values(ascending=False)
        if not cli_grp.empty:
            top_cli = cli_grp.index[0]
            insights.append(
                f"{top_cli} es el cliente con mayor facturación: "
                f"USD {cli_grp[top_cli]:,.0f}."
            )

    # 2. Destination mix
    if "destino" in df_com_filtered.columns and "kg_vendidos" in df_com_filtered.columns:
        dest_grp = df_com_filtered.groupby("destino")["kg_vendidos"].sum().sort_values(ascending=False)
        total_kg = dest_grp.sum()
        if total_kg > 0 and not dest_grp.empty:
            top_dest = dest_grp.index[0]
            p = pct(dest_grp[top_dest], total_kg)
            insights.append(
                f"El destino {top_dest} concentra el {p}% del volumen vendido."
            )

    # 3. Average price by calibre
    if "calibre" in df_com_filtered.columns and "precio_unitario_usd" in df_com_filtered.columns:
        cal_price = df_com_filtered.groupby("calibre")["precio_unitario_usd"].mean().sort_values(ascending=False)
        if not cal_price.empty:
            top_cal = cal_price.index[0]
            insights.append(
                f"El calibre {top_cal} obtiene el mejor precio promedio: "
                f"USD {cal_price[top_cal]:.3f}/kg."
            )

    # 4. Collection rate
    if "estado_cobro" in df_com_filtered.columns:
        total = len(df_com_filtered)
        cobrado = (df_com_filtered["estado_cobro"] == "Cobrado").sum()
        if total > 0:
            p = pct(cobrado, total)
            insights.append(
                f"El {p}% de las operaciones comerciales se encuentran cobradas."
            )

    # 5. Best margin canal
    if "canal" in df_com_filtered.columns and "margen_estimado" in df_com_filtered.columns:
        canal_margin = df_com_filtered.groupby("canal")["margen_estimado"].mean().sort_values(ascending=False)
        if not canal_margin.empty:
            top_canal = canal_margin.index[0]
            insights.append(
                f"El canal {top_canal} presenta el mayor margen promedio: "
                f"{canal_margin[top_canal] * 100:.1f}%."
            )

    return insights[:5] if insights else ["No se encontraron insights para el período seleccionado."]


def compute_insights_finanzas(df_fin_filtered: pd.DataFrame) -> List[str]:
    """Return 3-5 business insights in Spanish from the filtered finanzas DataFrame."""
    insights: List[str] = []
    if df_fin_filtered.empty:
        return ["No hay datos financieros para el período seleccionado."]

    ingresos = df_fin_filtered[df_fin_filtered["tipo"] == "Ingreso"]["importe"].sum()
    egresos = df_fin_filtered[df_fin_filtered["tipo"] == "Egreso"]["importe"].sum()
    flujo_neto = ingresos - egresos

    # 1. Net cash flow
    sign = "positivo" if flujo_neto >= 0 else "negativo"
    insights.append(
        f"El flujo de caja neto es {sign}: "
        f"Ingresos {ingresos:,.0f} vs Egresos {egresos:,.0f}."
    )

    # 2. Pending receivables
    cob = df_fin_filtered[
        (df_fin_filtered["tipo"] == "Ingreso") & (df_fin_filtered["estado"] != "Cobrado")
    ]["importe"].sum()
    if cob > 0:
        insights.append(
            f"Existen cuentas por cobrar pendientes por {cob:,.0f} (en la moneda del registro)."
        )

    # 3. Pending payables
    pag = df_fin_filtered[
        (df_fin_filtered["tipo"] == "Egreso") & (df_fin_filtered["estado"] != "Pagado")
    ]["importe"].sum()
    if pag > 0:
        insights.append(
            f"Las cuentas por pagar pendientes ascienden a {pag:,.0f}."
        )

    # 4. Top client/provider by amount
    if "cliente_proveedor" in df_fin_filtered.columns:
        cp_grp = df_fin_filtered.groupby("cliente_proveedor")["importe"].sum().sort_values(ascending=False)
        if not cp_grp.empty:
            top_cp = cp_grp.index[0]
            insights.append(
                f"{top_cp} es el cliente/proveedor con mayor movimiento financiero: "
                f"{cp_grp[top_cp]:,.0f}."
            )

    # 5. Highest cash pressure week
    if "fecha" in df_fin_filtered.columns and "tipo" in df_fin_filtered.columns:
        df_copy = df_fin_filtered.copy()
        if "semana" not in df_copy.columns:
            df_copy["semana"] = df_copy["fecha"].apply(week_label)
        df_copy["signo"] = df_copy["tipo"].map({"Ingreso": 1, "Egreso": -1}).fillna(0)
        df_copy["flujo"] = df_copy["importe"] * df_copy["signo"]
        weekly = df_copy.groupby("semana")["flujo"].sum().sort_values()
        if not weekly.empty:
            worst_week = weekly.index[0]
            worst_flow = weekly.iloc[0]
            insights.append(
                f"La mayor presión de caja se observa en {worst_week} con un flujo neto de "
                f"{worst_flow:,.0f}."
            )

    # 6. Bank/cash concentration
    if "banco_caja" in df_fin_filtered.columns:
        bc_grp = df_fin_filtered.groupby("banco_caja")["importe"].sum().sort_values(ascending=False)
        if not bc_grp.empty:
            top_bc = bc_grp.index[0]
            total_imp = bc_grp.sum()
            p = pct(bc_grp[top_bc], total_imp)
            insights.append(
                f"El {p}% del movimiento financiero se concentra en {top_bc}."
            )

    return insights[:5] if insights else ["No se encontraron insights para el período seleccionado."]


def compute_insights_costos(
    df_cos_filtered: pd.DataFrame, df_com_filtered: pd.DataFrame
) -> List[str]:
    """Return 3-5 business insights in Spanish from the costos/comercial DataFrames."""
    insights: List[str] = []
    if df_cos_filtered.empty:
        return ["No hay datos de costos para el período seleccionado."]

    total_costos = df_cos_filtered["importe"].sum()

    # 1. Cost breakdown by centro_costo
    if "centro_costo" in df_cos_filtered.columns:
        cc_grp = df_cos_filtered.groupby("centro_costo")["importe"].sum().sort_values(ascending=False)
        if not cc_grp.empty and total_costos > 0:
            top_cc = cc_grp.index[0]
            p = pct(cc_grp[top_cc], total_costos)
            insights.append(
                f"El centro de costo {top_cc} representa el {p}% del costo total "
                f"({cc_grp[top_cc]:,.0f})."
            )

    # 2. Most expensive lote
    if "lote" in df_cos_filtered.columns and "finca" in df_cos_filtered.columns:
        lote_grp = df_cos_filtered.groupby(["lote", "finca"])["importe"].sum().reset_index()
        if not lote_grp.empty:
            top_row = lote_grp.loc[lote_grp["importe"].idxmax()]
            insights.append(
                f"El lote {top_row['lote']} ({top_row['finca']}) acumula el mayor costo: "
                f"{top_row['importe']:,.0f}."
            )

    # 3. Canal with lowest margin (from comercial)
    if not df_com_filtered.empty and "canal" in df_com_filtered.columns and "margen_estimado" in df_com_filtered.columns:
        canal_margin = (
            df_com_filtered.groupby("canal")["margen_estimado"]
            .mean()
            .sort_values()
        )
        if not canal_margin.empty:
            worst_canal = canal_margin.index[0]
            insights.append(
                f"El canal {worst_canal} presenta el menor margen promedio: "
                f"{canal_margin[worst_canal] * 100:.1f}%."
            )

    # 4. Tipo_costo with most spend
    if "tipo_costo" in df_cos_filtered.columns:
        tipo_grp = df_cos_filtered.groupby("tipo_costo")["importe"].sum().sort_values(ascending=False)
        if not tipo_grp.empty and total_costos > 0:
            top_tipo = tipo_grp.index[0]
            p = pct(tipo_grp[top_tipo], total_costos)
            insights.append(
                f"El tipo de costo '{top_tipo}' es el más relevante con el {p}% del total."
            )

    # 5. Cost trend (compare first vs last week)
    if "fecha" in df_cos_filtered.columns and len(df_cos_filtered) > 1:
        df_cos_filtered = df_cos_filtered.copy()
        if "semana" not in df_cos_filtered.columns:
            df_cos_filtered["semana"] = df_cos_filtered["fecha"].apply(week_label)
        weekly = df_cos_filtered.groupby("semana")["importe"].sum().sort_index()
        if len(weekly) >= 2:
            primera = weekly.iloc[0]
            ultima = weekly.iloc[-1]
            if primera > 0:
                variacion = ((ultima - primera) / primera) * 100
                tendencia = "aumentó" if variacion > 0 else "disminuyó"
                insights.append(
                    f"El costo semanal {tendencia} un {abs(variacion):.1f}% desde la primera "
                    f"semana del período analizado."
                )

    return insights[:5] if insights else ["No se encontraron insights para el período seleccionado."]
