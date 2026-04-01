"""
Generador de datos mock realistas para la plataforma BI de limón.

La lógica prioriza coherencia entre módulos:
- Campo define la curva de cosecha y el costo base por lote.
- Empaque se alimenta de la fruta cosechada.
- Comercial surge de los kilos procesados por lote.
- Costos y finanzas nacen de la operación real simulada.
"""

from __future__ import annotations

import os
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

np.random.seed(42)
random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

CAMPAIGNS = [2023, 2024]
KG_POR_CAJA = 18

FINCAS = {
    "La Esperanza": {
        "lotes": ["LE-01", "LE-02", "LE-03", "LE-04"],
        "ha": [30, 35, 28, 27],
        "encargado": "Roberto Pérez",
        "variedad": ["Eureka", "Eureka", "Lisbon", "Génova"],
        "quality_factor": [0.74, 0.71, 0.67, 0.63],
    },
    "San Cayetano": {
        "lotes": ["SC-01", "SC-02", "SC-03"],
        "ha": [30, 28, 27],
        "encargado": "Carlos Juárez",
        "variedad": ["Eureka", "Lisbon", "Génova"],
        "quality_factor": [0.72, 0.65, 0.58],
    },
    "El Paraíso": {
        "lotes": ["EP-01", "EP-02", "EP-03", "EP-04"],
        "ha": [25, 30, 22, 18],
        "encargado": "Miguel Flores",
        "variedad": ["Eureka", "Eureka", "Lisbon", "Génova"],
        "quality_factor": [0.76, 0.73, 0.68, 0.61],
    },
    "Río Ancho": {
        "lotes": ["RA-01", "RA-02", "RA-03"],
        "ha": [40, 38, 32],
        "encargado": "Juan Nieva",
        "variedad": ["Eureka", "Lisbon", "Génova"],
        "quality_factor": [0.69, 0.64, 0.55],
    },
    "Los Álamos": {
        "lotes": ["LA-01", "LA-02", "LA-03"],
        "ha": [28, 25, 22],
        "encargado": "Sebastián Gómez",
        "variedad": ["Eureka", "Lisbon", "Génova"],
        "quality_factor": [0.70, 0.66, 0.59],
    },
}

YIELD_KG_HA = {
    "Eureka": 38000,
    "Lisbon": 33000,
    "Génova": 28000,
}

CLIENTES = {
    "Exportación": [
        {"nombre": "Fischer Import GmbH", "pais": "Alemania", "precio_base_usd": 0.39},
        {"nombre": "Citrus World Ltd", "pais": "Reino Unido", "precio_base_usd": 0.37},
        {"nombre": "Medifresh SA", "pais": "España", "precio_base_usd": 0.35},
        {"nombre": "Al Salam Trading", "pais": "Emiratos Árabes", "precio_base_usd": 0.33},
    ],
    "Mercado Interno": [
        {"nombre": "La Morenita SA", "pais": "Tucumán", "precio_base_usd": 0.22},
        {"nombre": "Frutales del Norte SRL", "pais": "Salta", "precio_base_usd": 0.20},
        {"nombre": "Central de Frutas SA", "pais": "Buenos Aires", "precio_base_usd": 0.23},
        {"nombre": "Supermercados Norte SA", "pais": "Tucumán", "precio_base_usd": 0.21},
    ],
    "Industria": [
        {"nombre": "Citromax SA", "pais": "Tucumán", "precio_base_usd": 0.075},
        {"nombre": "Frutales Tucumán SRL", "pais": "Tucumán", "precio_base_usd": 0.068},
    ],
}

CHANNELS = {
    "Exportación": ["Exportación Directa", "Programa Retail UE", "Trader Golfo"],
    "Mercado Interno": ["Retail Nacional", "Mercado Central", "Distribuidor Regional"],
    "Industria": ["Contrato Industria", "Mercado Industrial"],
}

PROVEEDORES = {
    "Campo": ["Cooperativa Citrícola", "Agroinsumos SA", "Servicios Rurales del NOA"],
    "Empaque": ["Envases del Tucumán", "Energía Tucumán SA", "TecnoPacking SRL"],
    "Logística": ["Transportes del Norte SA", "FríoAndes Logística", "Despachos del NOA"],
    "Administración": ["AFIP", "DGR Tucumán", "Contaduría Castillo"],
    "Comercial": ["Certificaciones Global GAP", "Broker Comercial Citrus", "Promoción de Mercados SA"],
}

CONCEPTOS_EGRESO = {
    "Campo": ["Mano de obra cosecha", "Insumos agrícolas", "Fitosanitarios", "Riego", "Maquinaria"],
    "Empaque": ["Mano de obra empaque", "Envases y embalajes", "Energía", "Mantenimiento líneas", "Control de calidad"],
    "Logística": ["Flete interno", "Flete exportación", "Frigorífico", "Despacho aduana"],
    "Administración": ["Sueldos administración", "Impuestos", "Seguros", "Honorarios", "Gastos generales"],
    "Comercial": ["Comisiones", "Certificaciones", "Promoción comercial", "Viajes comerciales"],
}

CALIBRES = ["2", "3", "4", "5", "6", "7"]
CALIDADES = ["Extra", "Primera", "Segunda"]
TURNOS = ["Mañana", "Tarde", "Noche"]
LINEAS = ["Línea 1", "Línea 2", "Línea 3"]
BANCOS = ["Banco Galicia", "Banco Nación", "Caja Operativa", "Banco BBVA"]


def get_lote_profiles() -> list[dict]:
    profiles = []
    for finca, meta in FINCAS.items():
        for idx, lote in enumerate(meta["lotes"]):
            profiles.append(
                {
                    "finca": finca,
                    "lote": lote,
                    "hectareas": meta["ha"][idx],
                    "encargado": meta["encargado"],
                    "variedad": meta["variedad"][idx],
                    "quality_factor": meta["quality_factor"][idx],
                }
            )
    return profiles


LOTE_PROFILES = get_lote_profiles()
LOT_META = {(p["finca"], p["lote"]): p for p in LOTE_PROFILES}


def get_dolar(fecha: date) -> float:
    if fecha.year == 2023:
        t = (fecha - date(2023, 1, 1)).days / 365
        return round(210 + t * 175 + np.random.normal(0, 5), 2)
    t = (fecha - date(2024, 1, 1)).days / 365
    return round(860 + t * 185 + np.random.normal(0, 15), 2)


def season_weight(fecha: date) -> float:
    weights = {3: 0.30, 4: 0.70, 5: 0.92, 6: 1.00, 7: 1.00, 8: 0.86, 9: 0.64, 10: 0.34, 11: 0.15}
    return weights.get(fecha.month, 0.0)


def get_week_dates(year: int) -> list[date]:
    dates = []
    current = date(year, 3, 1)
    end = date(year, 11, 30)
    while current <= end:
        dates.append(current)
        current += timedelta(weeks=1)
    return dates


def clip(value: float, minimum: float, maximum: float) -> float:
    return float(np.clip(value, minimum, maximum))


def pick_calibre(variedad: str, export_share: float) -> str:
    if variedad == "Eureka":
        weights = [0.08, 0.18, 0.28, 0.22, 0.16, 0.08]
    elif variedad == "Lisbon":
        weights = [0.05, 0.14, 0.27, 0.26, 0.18, 0.10]
    else:
        weights = [0.04, 0.10, 0.22, 0.27, 0.22, 0.15]

    if export_share > 0.74:
        weights = [w * adj for w, adj in zip(weights, [1.15, 1.10, 1.05, 0.95, 0.90, 0.85])]
    elif export_share < 0.60:
        weights = [w * adj for w, adj in zip(weights, [0.90, 0.92, 1.00, 1.05, 1.08, 1.10])]

    return random.choices(CALIBRES, weights=weights, k=1)[0]


def pick_calidad(export_share: float, discard_share: float) -> str:
    if export_share >= 0.74 and discard_share <= 0.06:
        return random.choices(CALIDADES, weights=[0.55, 0.35, 0.10], k=1)[0]
    if export_share >= 0.66:
        return random.choices(CALIDADES, weights=[0.25, 0.55, 0.20], k=1)[0]
    return random.choices(CALIDADES, weights=[0.10, 0.45, 0.45], k=1)[0]


def normalize_shares(*parts: float) -> list[float]:
    total = sum(parts)
    if total <= 0:
        return [0.0 for _ in parts]
    return [part / total for part in parts]


def allocate_amount(total: float, allocations: list[tuple[str, float]]) -> list[tuple[str, float]]:
    valid = [(label, max(0.0, float(weight))) for label, weight in allocations if weight > 0]
    if total <= 0 or not valid:
        return []

    labels = [label for label, _ in valid]
    weights = np.array([weight for _, weight in valid], dtype=float)
    weights = weights / weights.sum()
    amounts = np.round(total * weights, 2)
    diff = round(float(total) - float(amounts.sum()), 2)
    amounts[int(np.argmax(amounts))] = round(float(amounts[int(np.argmax(amounts))]) + diff, 2)
    return [(labels[idx], float(amount)) for idx, amount in enumerate(amounts) if amount > 0]


def harvest_completion_target(campaign_year: int, variedad: str, quality_factor: float) -> float:
    base_by_variety = {"Eureka": 0.982, "Lisbon": 0.966, "Génova": 0.946}
    year_boost = 0.0 if campaign_year == 2023 else 0.012
    quality_boost = (quality_factor - 0.66) * 0.10
    random_shift = np.random.uniform(-0.02, 0.02)
    closeout_bonus = np.random.uniform(0.012, 0.03) if np.random.random() < (0.44 if campaign_year == 2023 else 0.58) else 0.0
    return clip(base_by_variety[variedad] + year_boost + quality_boost + random_shift + closeout_bonus, 0.90, 1.0)


def harvest_timing_factor(variedad: str, month: int) -> float:
    if variedad == "Eureka":
        return {3: 0.95, 4: 1.08, 5: 1.12, 6: 1.08, 7: 1.00, 8: 0.94, 9: 0.86, 10: 0.74, 11: 0.62}.get(month, 0.0)
    if variedad == "Lisbon":
        return {3: 0.84, 4: 0.96, 5: 1.04, 6: 1.08, 7: 1.07, 8: 1.00, 9: 0.90, 10: 0.78, 11: 0.60}.get(month, 0.0)
    return {3: 0.74, 4: 0.88, 5: 0.98, 6: 1.04, 7: 1.08, 8: 1.08, 9: 0.98, 10: 0.84, 11: 0.66}.get(month, 0.0)


def channel_mix_by_keys(comercial_df: pd.DataFrame, group_keys: list[str]) -> dict[tuple, dict[str, float]]:
    grouped = (
        comercial_df.groupby(group_keys + ["canal"])
        .agg(kg_vendidos=("kg_vendidos", "sum"))
        .reset_index()
    )
    mixes: dict[tuple, dict[str, float]] = {}
    for key, group in grouped.groupby(group_keys):
        key_tuple = key if isinstance(key, tuple) else (key,)
        total = float(group["kg_vendidos"].sum())
        if total <= 0:
            continue
        mixes[key_tuple] = {
            str(row["canal"]): float(row["kg_vendidos"]) / total for _, row in group.iterrows()
        }
    return mixes


def channel_allocations(total: float, channel_mix: dict[str, float], general_share: float) -> list[tuple[str, float]]:
    allocations = [("General", max(0.0, min(1.0, general_share)))]
    variable_share = max(0.0, 1.0 - allocations[0][1])
    for canal, share in channel_mix.items():
        allocations.append((canal, variable_share * share))
    return allocate_amount(total, allocations)


def status_cobro(fecha: date, year: int) -> str:
    ref = date(year, 11, 30)
    edad = (ref - fecha).days
    if edad >= 75:
        return random.choices(["Cobrado", "Pendiente", "Vencido"], weights=[0.84, 0.13, 0.03], k=1)[0]
    if edad >= 30:
        return random.choices(["Cobrado", "Pendiente", "Vencido"], weights=[0.58, 0.30, 0.12], k=1)[0]
    return random.choices(["Cobrado", "Pendiente"], weights=[0.20, 0.80], k=1)[0]


def status_pedido(destino: str, fecha: date, year: int) -> str:
    ref = date(year, 11, 30)
    edad = (ref - fecha).days
    if destino == "Industria":
        return random.choices(["Cumplido", "Parcial"], weights=[0.88, 0.12], k=1)[0]
    if edad >= 45:
        return random.choices(["Cumplido", "Parcial"], weights=[0.90, 0.10], k=1)[0]
    return random.choices(["Cumplido", "Parcial", "Pendiente"], weights=[0.55, 0.25, 0.20], k=1)[0]


def generate_campo() -> pd.DataFrame:
    rows: list[dict] = []

    for campaign_year in CAMPAIGNS:
        campaign = str(campaign_year)
        campaign_yield_factor = 1.0 if campaign_year == 2023 else 1.06
        cost_ha_range = (680_000, 1_040_000) if campaign_year == 2023 else (1_650_000, 2_380_000)
        weeks = get_week_dates(campaign_year)
        active_weeks = [week for week in weeks if season_weight(week) > 0]

        for profile in LOTE_PROFILES:
            ha = profile["hectareas"]
            variedad = profile["variedad"]
            base_yield = YIELD_KG_HA[variedad] * campaign_yield_factor
            prod_estimada = ha * base_yield * np.random.uniform(0.93, 1.07)
            prod_real = prod_estimada * np.random.uniform(0.90, 1.03)
            costo_ha = round(np.random.uniform(*cost_ha_range), 0)
            target_completion = harvest_completion_target(campaign_year, variedad, profile["quality_factor"])
            target_cosecha = round(prod_real * target_completion, 0)

            weekly_weights = []
            for week in active_weeks:
                weight = season_weight(week) * harvest_timing_factor(variedad, week.month) * np.random.uniform(0.86, 1.16)
                weekly_weights.append(max(0.01, weight))
            weekly_weights = np.array(weekly_weights, dtype=float)
            weekly_weights = weekly_weights / weekly_weights.sum()
            cumulative_plan = np.maximum.accumulate(np.round(np.cumsum(weekly_weights * target_cosecha), 0))
            cumulative_plan[-1] = target_cosecha

            kg_cosechados_acum = 0.0
            for idx, week in enumerate(active_weeks):
                planned_cumulative = float(cumulative_plan[idx])
                kg_semana = max(0.0, planned_cumulative - kg_cosechados_acum)
                kg_cosechados_acum += kg_semana

                kg_pendientes = max(0.0, prod_real - kg_cosechados_acum)
                avance = kg_cosechados_acum / prod_real if prod_real else 0.0
                if avance < 0.72:
                    estado = "En cosecha"
                elif avance < 0.985:
                    estado = "Finalizando"
                else:
                    estado = "Completado"

                rows.append(
                    {
                        "fecha": week.isoformat(),
                        "campaña": campaign,
                        "finca": profile["finca"],
                        "lote": profile["lote"],
                        "variedad": variedad,
                        "hectareas": ha,
                        "encargado": profile["encargado"],
                        "produccion_estimada_kg": round(prod_estimada, 0),
                        "produccion_real_kg": round(prod_real, 0),
                        "kg_cosechados": round(kg_cosechados_acum, 0),
                        "kg_pendientes": round(kg_pendientes, 0),
                        "costo_por_ha": costo_ha,
                        "costo_total_lote": round(costo_ha * ha, 0),
                        "estado_cosecha": estado,
                        "rendimiento_kg_ha": round(kg_cosechados_acum / ha, 1),
                    }
                )

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(DATA_DIR, "campo.csv"), index=False)
    print(f"campo.csv: {len(df)} filas")
    return df


def build_weekly_cosecha(campo_df: pd.DataFrame) -> pd.DataFrame:
    df = campo_df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values(["campaña", "finca", "lote", "fecha"])
    df["kg_semana"] = df.groupby(["campaña", "finca", "lote"])["kg_cosechados"].diff()
    df["kg_semana"] = df["kg_semana"].fillna(df["kg_cosechados"])
    return df[df["kg_semana"] > 0].copy()


def generate_empaque(campo_df: pd.DataFrame) -> pd.DataFrame:
    weekly = build_weekly_cosecha(campo_df)
    rows: list[dict] = []

    for row in weekly.itertuples(index=False):
        week_date = pd.Timestamp(row.fecha).date()
        base_quality = LOT_META[(row.finca, row.lote)]["quality_factor"]
        season_adj = (season_weight(week_date) - 0.55) * 0.10
        kg_semana = float(row.kg_semana)
        if kg_semana <= 0:
            continue

        batches = max(1, min(4, int(round(kg_semana / 32_000))))
        shares = np.random.dirichlet(np.ones(batches))
        assigned_kg = 0.0

        for idx, share in enumerate(shares):
            kg_ing = round(kg_semana * share * np.random.uniform(0.985, 1.015), 0)
            if idx == len(shares) - 1:
                remaining = max(0.0, kg_semana - assigned_kg)
                if remaining > 0:
                    kg_ing = round(remaining, 0)
            assigned_kg += kg_ing

            export_share = clip(base_quality + season_adj + np.random.normal(0, 0.025), 0.50, 0.82)
            industria_share = clip(0.14 + (0.74 - export_share) * 0.32 + np.random.uniform(-0.01, 0.03), 0.10, 0.28)
            descarte_share = max(0.04, 1 - export_share - industria_share)
            export_share, industria_share, descarte_share = normalize_shares(export_share, industria_share, descarte_share)

            calibre = pick_calibre(row.variedad, export_share)
            calidad = pick_calidad(export_share, descarte_share)
            turno = random.choices(TURNOS, weights=[0.38, 0.37, 0.25], k=1)[0]
            linea = random.choice(LINEAS)

            kg_export = round(kg_ing * export_share, 0)
            kg_industria = round(kg_ing * industria_share, 0)
            kg_descarte = round(max(0.0, kg_ing - kg_export - kg_industria), 0)

            cajas = round(kg_export / KG_POR_CAJA, 0)
            productividad = np.random.uniform(78, 118)
            horas = round(max(4.5, cajas / productividad), 1)
            costo_empaque = round(kg_ing * np.random.uniform(0.058, 0.082), 2)

            rows.append(
                {
                    "fecha": week_date.isoformat(),
                    "campaña": str(row.campaña),
                    "finca": row.finca,
                    "lote": row.lote,
                    "variedad": row.variedad,
                    "kg_ingresados": kg_ing,
                    "kg_exportables": kg_export,
                    "kg_industria": kg_industria,
                    "kg_descarte": kg_descarte,
                    "calibre": calibre,
                    "calidad": calidad,
                    "turno": turno,
                    "linea": linea,
                    "cajas_producidas": cajas,
                    "horas_operativas": horas,
                    "costo_empaque": costo_empaque,
                    "rendimiento_exportable_pct": round(export_share * 100, 1),
                }
            )

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(DATA_DIR, "empaque.csv"), index=False)
    print(f"empaque.csv: {len(df)} filas")
    return df


def weekly_lot_summary(empaque_df: pd.DataFrame) -> pd.DataFrame:
    df = empaque_df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"])

    grouped = (
        df.groupby(["fecha", "campaña", "finca", "lote", "variedad"])
        .agg(
            kg_exportables=("kg_exportables", "sum"),
            kg_industria=("kg_industria", "sum"),
            kg_descarte=("kg_descarte", "sum"),
            calibre_dominante=("calibre", lambda s: str(s.mode().iloc[0]) if not s.mode().empty else ""),
            calidad_dominante=("calidad", lambda s: s.mode().iloc[0] if not s.mode().empty else ""),
        )
        .reset_index()
    )
    return grouped


def generate_comercial(empaque_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    lot_week = weekly_lot_summary(empaque_df)
    counter = 1

    for row in lot_week.itertuples(index=False):
        year = int(row.campaña)
        sale_date = pd.Timestamp(row.fecha).date()
        dolar = get_dolar(sale_date)
        season_bonus = (season_weight(sale_date) - 0.5) * 0.08
        calibre = str(row.calibre_dominante or random.choice(CALIBRES))
        calidad = row.calidad_dominante or "Primera"

        premium_calibre = {"2": 0.08, "3": 0.05, "4": 0.02, "5": 0.00, "6": -0.04, "7": -0.08}.get(calibre, 0.0)
        premium_calidad = {"Extra": 0.04, "Primera": 0.0, "Segunda": -0.06}.get(calidad, 0.0)

        kg_export = float(row.kg_exportables)
        kg_industria = float(row.kg_industria)
        export_ratio = clip(0.72 + premium_calidad * 0.8 + premium_calibre * 0.5 + np.random.uniform(-0.05, 0.06), 0.58, 0.86)
        kg_exportacion = round(kg_export * export_ratio, 0)
        kg_interno = round(max(0.0, kg_export - kg_exportacion), 0)

        sales_plan = [
            ("Exportación", kg_exportacion),
            ("Mercado Interno", kg_interno),
            ("Industria", round(kg_industria, 0)),
        ]

        for destino, kg_total in sales_plan:
            if kg_total < 1_500:
                continue

            n_ops = 2 if destino == "Exportación" and kg_total > 24_000 else 1
            shares = np.random.dirichlet(np.ones(n_ops))
            for share in shares:
                kg = round(kg_total * share, 0)
                if kg <= 0:
                    continue

                client = random.choice(CLIENTES[destino])
                channel = random.choice(CHANNELS[destino])
                price = client["precio_base_usd"] * (1 + season_bonus + premium_calibre + premium_calidad)
                if destino == "Exportación":
                    price *= np.random.uniform(0.96, 1.08)
                    margin = clip(np.random.uniform(0.18, 0.31) + premium_calidad * 0.45, 0.12, 0.34)
                elif destino == "Mercado Interno":
                    price *= np.random.uniform(0.95, 1.07)
                    margin = clip(np.random.uniform(0.11, 0.21) + premium_calidad * 0.20, 0.08, 0.23)
                else:
                    price *= np.random.uniform(0.94, 1.04)
                    margin = clip(np.random.uniform(0.03, 0.09), 0.02, 0.11)

                importe_usd = round(kg * price, 2)
                importe_ars = round(importe_usd * dolar, 2)

                rows.append(
                    {
                        "fecha": sale_date.isoformat(),
                        "campaña": str(row.campaña),
                        "pedido_id": f"PED-{year}-{counter:05d}",
                        "finca": row.finca,
                        "lote": row.lote,
                        "variedad": row.variedad,
                        "cliente": client["nombre"],
                        "destino": destino,
                        "pais_provincia": client["pais"],
                        "canal": channel,
                        "producto": "Limón Industria" if destino == "Industria" else f"Limón {row.variedad}",
                        "calibre": calibre,
                        "calidad": calidad,
                        "kg_vendidos": kg,
                        "cajas": round(kg / KG_POR_CAJA, 0),
                        "precio_unitario_usd": round(price, 4),
                        "importe_usd": importe_usd,
                        "tipo_cambio": dolar,
                        "importe_ars": importe_ars,
                        "margen_estimado": round(margin, 4),
                        "moneda": "USD" if destino == "Exportación" else "ARS",
                        "estado_cobro": status_cobro(sale_date, year),
                        "estado_pedido": status_pedido(destino, sale_date, year),
                    }
                )
                counter += 1

    df = pd.DataFrame(rows).sort_values(["fecha", "destino", "cliente"]).reset_index(drop=True)
    df.to_csv(os.path.join(DATA_DIR, "comercial.csv"), index=False)
    print(f"comercial.csv: {len(df)} filas")
    return df


def generate_costos(campo_df: pd.DataFrame, empaque_df: pd.DataFrame, comercial_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    campo_weekly = build_weekly_cosecha(campo_df)
    lot_channel_mix = channel_mix_by_keys(comercial_df, ["campaña", "finca", "lote"])
    campaign_channel_mix = channel_mix_by_keys(comercial_df, ["campaña"])
    campo_last = campo_df.copy()
    campo_last["fecha"] = pd.to_datetime(campo_last["fecha"])
    campo_last = campo_last.sort_values("fecha").groupby(["campaña", "finca", "lote"], as_index=False).last()
    campo_totals = {
        (str(row.campaña), row.finca, row.lote): {
            "kg_total": float(row.produccion_real_kg),
            "costo_total": float(row.costo_total_lote),
            "hectareas": float(row.hectareas),
        }
        for row in campo_last.itertuples(index=False)
    }

    empaque_week = (
        empaque_df.assign(fecha=pd.to_datetime(empaque_df["fecha"]))
        .groupby(["fecha", "campaña", "finca", "lote"])
        .agg(
            kg_ingresados=("kg_ingresados", "sum"),
            costo_empaque_usd=("costo_empaque", "sum"),
        )
        .reset_index()
    )

    for row in campo_weekly.itertuples(index=False):
        key = (str(row.campaña), row.finca, row.lote)
        lote_total = campo_totals[key]
        mix = lot_channel_mix.get(key, {})
        share = float(row.kg_semana) / max(lote_total["kg_total"], 1.0)
        importe = round(lote_total["costo_total"] * share * np.random.uniform(0.97, 1.03), 2)
        allocations = channel_allocations(importe, mix, general_share=np.random.uniform(0.34, 0.46))
        for canal, allocated in allocations:
            rows.append(
                {
                    "fecha": pd.Timestamp(row.fecha).date().isoformat(),
                    "campaña": str(row.campaña),
                    "finca": row.finca,
                    "lote": row.lote,
                    "centro_costo": "Campo",
                    "tipo_costo": random.choice(CONCEPTOS_EGRESO["Campo"]),
                    "canal": canal,
                    "importe": allocated,
                    "moneda": "ARS",
                }
            )

    for row in empaque_week.itertuples(index=False):
        dolar = get_dolar(pd.Timestamp(row.fecha).date())
        key = (str(row.campaña), row.finca, row.lote)
        mix = lot_channel_mix.get(key, {})
        importe = round(float(row.costo_empaque_usd) * dolar, 2)
        allocations = channel_allocations(importe, mix, general_share=np.random.uniform(0.18, 0.28))
        for canal, allocated in allocations:
            rows.append(
                {
                    "fecha": pd.Timestamp(row.fecha).date().isoformat(),
                    "campaña": str(row.campaña),
                    "finca": row.finca,
                    "lote": row.lote,
                    "centro_costo": "Empaque",
                    "tipo_costo": random.choice(CONCEPTOS_EGRESO["Empaque"]),
                    "canal": canal,
                    "importe": allocated,
                    "moneda": "ARS",
                }
            )

    for row in comercial_df.itertuples(index=False):
        year_factor = 0.48 if int(row.campaña) == 2023 else 1.0
        if row.destino == "Exportación":
            log_rate = np.random.uniform(72, 96) * year_factor
            comercial_rate = np.random.uniform(28, 44)
        elif row.destino == "Mercado Interno":
            log_rate = np.random.uniform(28, 42) * year_factor
            comercial_rate = np.random.uniform(12, 24)
        else:
            log_rate = np.random.uniform(14, 24) * year_factor
            comercial_rate = np.random.uniform(6, 12)

        rows.append(
            {
                "fecha": row.fecha,
                "campaña": row.campaña,
                "finca": row.finca,
                "lote": row.lote,
                "centro_costo": "Logística",
                "tipo_costo": random.choice(CONCEPTOS_EGRESO["Logística"]),
                "canal": row.canal,
                "importe": round(float(row.kg_vendidos) * log_rate, 2),
                "moneda": "ARS",
            }
        )
        rows.append(
            {
                "fecha": row.fecha,
                "campaña": row.campaña,
                "finca": row.finca,
                "lote": row.lote,
                "centro_costo": "Comercial",
                "tipo_costo": random.choice(CONCEPTOS_EGRESO["Comercial"]),
                "canal": row.canal,
                "importe": round(float(row.importe_ars) * np.random.uniform(comercial_rate / 1000, (comercial_rate + 6) / 1000), 2),
                "moneda": "ARS",
            }
        )

    for row in campo_weekly.itertuples(index=False):
        year = str(row.campaña)
        admin_range = (5_800, 8_800) if int(row.campaña) == 2023 else (10_500, 16_500)
        admin_base = LOT_META[(row.finca, row.lote)]["hectareas"] * np.random.uniform(*admin_range)
        mix = lot_channel_mix.get((year, row.finca, row.lote), campaign_channel_mix.get((year,), {}))
        allocations = channel_allocations(round(admin_base, 2), mix, general_share=np.random.uniform(0.66, 0.78))
        for canal, allocated in allocations:
            rows.append(
                {
                    "fecha": pd.Timestamp(row.fecha).date().isoformat(),
                    "campaña": year,
                    "finca": row.finca,
                    "lote": row.lote,
                    "centro_costo": "Administración",
                    "tipo_costo": random.choice(CONCEPTOS_EGRESO["Administración"]),
                    "canal": canal,
                    "importe": allocated,
                    "moneda": "ARS",
                }
            )

    df = pd.DataFrame(rows).sort_values(["fecha", "finca", "lote"]).reset_index(drop=True)
    df.to_csv(os.path.join(DATA_DIR, "costos.csv"), index=False)
    print(f"costos.csv: {len(df)} filas")
    return df


def finance_status(vencimiento: date, campaign_year: int, flow_type: str) -> str:
    ref = date(campaign_year, 11, 30)
    delta = (ref - vencimiento).days
    if flow_type == "Ingreso":
        if delta >= 30:
            return random.choices(["Cobrado", "Pendiente", "Vencido"], weights=[0.80, 0.15, 0.05], k=1)[0]
        if delta >= 0:
            return random.choices(["Cobrado", "Pendiente", "Vencido"], weights=[0.45, 0.40, 0.15], k=1)[0]
        return random.choices(["Cobrado", "Pendiente"], weights=[0.20, 0.80], k=1)[0]
    if delta >= 20:
        return random.choices(["Pagado", "Pendiente", "Vencido"], weights=[0.78, 0.17, 0.05], k=1)[0]
    if delta >= 0:
        return random.choices(["Pagado", "Pendiente", "Vencido"], weights=[0.48, 0.37, 0.15], k=1)[0]
    return random.choices(["Pagado", "Pendiente"], weights=[0.22, 0.78], k=1)[0]


def generate_finanzas(comercial_df: pd.DataFrame, costos_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []

    for row in comercial_df.itertuples(index=False):
        year = int(row.campaña)
        fecha = pd.Timestamp(row.fecha).date()
        if row.destino == "Exportación":
            plazo = random.randint(18, 40)
        elif row.destino == "Mercado Interno":
            plazo = random.randint(10, 24)
        else:
            plazo = random.randint(20, 45)
        vencimiento = fecha + timedelta(days=plazo)
        rows.append(
            {
                "fecha": fecha.isoformat(),
                "campaña": row.campaña,
                "tipo": "Ingreso",
                "concepto": f"Venta {row.destino}",
                "cliente_proveedor": row.cliente,
                "importe": round(float(row.importe_ars), 2),
                "moneda": "ARS",
                "vencimiento": vencimiento.isoformat(),
                "estado": finance_status(vencimiento, year, "Ingreso"),
                "banco_caja": random.choice(BANCOS),
                "categoria_flujo": "Operaciones",
            }
        )

    grouped_costs = (
        costos_df.assign(fecha=pd.to_datetime(costos_df["fecha"]))
        .groupby(["fecha", "campaña", "centro_costo", "tipo_costo"])
        .agg(importe=("importe", "sum"))
        .reset_index()
    )
    for row in grouped_costs.itertuples(index=False):
        year = int(row.campaña)
        fecha = pd.Timestamp(row.fecha).date()
        plazo = random.randint(5, 18) if row.centro_costo != "Administración" else random.randint(10, 25)
        vencimiento = fecha + timedelta(days=plazo)
        proveedor = random.choice(PROVEEDORES[row.centro_costo])
        rows.append(
            {
                "fecha": fecha.isoformat(),
                "campaña": str(row.campaña),
                "tipo": "Egreso",
                "concepto": row.tipo_costo,
                "cliente_proveedor": proveedor,
                "importe": round(float(row.importe), 2),
                "moneda": "ARS",
                "vencimiento": vencimiento.isoformat(),
                "estado": finance_status(vencimiento, year, "Egreso"),
                "banco_caja": random.choice(BANCOS),
                "categoria_flujo": "Operaciones" if row.centro_costo != "Administración" else random.choice(["Operaciones", "Impuestos"]),
            }
        )

    financing_events = [
        ("Ingreso", "Desembolso descubierto campaña", "Banco Galicia - Línea Campaña", 180_000_000),
        ("Ingreso", "Adelanto exportación", "Banco Nación - Prefinanciación", 240_000_000),
        ("Egreso", "Repago descubierto campaña", "Banco Galicia - Línea Campaña", 130_000_000),
        ("Egreso", "Repago prefinanciación", "Banco Nación - Prefinanciación", 210_000_000),
    ]
    for year in CAMPAIGNS:
        schedule = [
            (date(year, 5, 20), financing_events[0]),
            (date(year, 6, 25), financing_events[1]),
            (date(year, 9, 18), financing_events[2]),
            (date(year, 10, 25), financing_events[3]),
        ]
        for event_date, (flow_type, concept, counterparty, amount) in schedule:
            vencimiento = event_date + timedelta(days=30)
            if year == 2023:
                multiplier = np.random.uniform(1.16, 1.28) if flow_type == "Ingreso" else np.random.uniform(0.94, 1.02)
            else:
                multiplier = np.random.uniform(0.94, 1.04)
            rows.append(
                {
                    "fecha": event_date.isoformat(),
                    "campaña": str(year),
                    "tipo": flow_type,
                    "concepto": concept,
                    "cliente_proveedor": counterparty,
                    "importe": round(amount * multiplier, 2),
                    "moneda": "ARS",
                    "vencimiento": vencimiento.isoformat(),
                    "estado": "Cobrado" if flow_type == "Ingreso" else "Pagado",
                    "banco_caja": random.choice(BANCOS),
                    "categoria_flujo": "Financiamiento",
                }
            )

    df = pd.DataFrame(rows).sort_values(["fecha", "tipo", "concepto"]).reset_index(drop=True)
    df.to_csv(os.path.join(DATA_DIR, "finanzas.csv"), index=False)
    print(f"finanzas.csv: {len(df)} filas")
    return df


def generate_contexto() -> pd.DataFrame:
    rows: list[dict] = []

    for campaign_year in CAMPAIGNS:
        current = date(campaign_year, 3, 1)
        end = date(campaign_year, 11, 30)
        while current <= end:
            dolar = get_dolar(current)
            month = current.month

            if month in [3, 4, 5]:
                t_min = np.random.uniform(10, 16)
                t_max = np.random.uniform(22, 29)
            elif month in [6, 7, 8]:
                t_min = np.random.uniform(4, 10)
                t_max = np.random.uniform(16, 22)
            else:
                t_min = np.random.uniform(10, 16)
                t_max = np.random.uniform(22, 27)

            if month in [3, 11]:
                lluvia = max(0, np.random.exponential(4.2))
            elif month in [4, 5, 10]:
                lluvia = max(0, np.random.exponential(2.0))
            else:
                lluvia = max(0, np.random.exponential(0.85))

            precio_ref = 0.29 + season_weight(current) * 0.11 + np.random.normal(0, 0.012)
            precio_ref = round(max(0.20, precio_ref), 3)
            riesgo = round(np.clip(lluvia * 0.32 + max(0, 30 - t_max) * 0.18 + np.random.uniform(0, 1.4), 0, 10), 2)

            rows.append(
                {
                    "fecha": current.isoformat(),
                    "campaña": str(campaign_year),
                    "dolar_referencia": dolar,
                    "lluvia_mm": round(lluvia, 2),
                    "temperatura_min": round(t_min, 1),
                    "temperatura_max": round(t_max, 1),
                    "precio_referencia_usd": precio_ref,
                    "indice_riesgo_climatico": riesgo,
                }
            )
            current += timedelta(days=1)

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(DATA_DIR, "contexto.csv"), index=False)
    print(f"contexto.csv: {len(df)} filas")
    return df


def generate_all() -> None:
    print("Generando datasets mock coherentes...")
    campo_df = generate_campo()
    empaque_df = generate_empaque(campo_df)
    comercial_df = generate_comercial(empaque_df)
    costos_df = generate_costos(campo_df, empaque_df, comercial_df)
    generate_finanzas(comercial_df, costos_df)
    generate_contexto()
    print("\nTodos los datasets fueron actualizados en backend/data/")


if __name__ == "__main__":
    generate_all()
