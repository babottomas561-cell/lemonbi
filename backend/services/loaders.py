"""Data loaders - load and cache CSV files as DataFrames."""
import os
from functools import lru_cache

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@lru_cache(maxsize=None)
def _read_csv(path: str, parse_dates: tuple[str, ...], mtime: float) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=list(parse_dates))

    if "campaña" in df.columns:
        df["campaña_str"] = df["campaña"].astype(str)

    if "fecha" in df.columns:
        iso = df["fecha"].dt.isocalendar()
        df["semana"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
        df["mes"] = df["fecha"].dt.strftime("%Y-%m")

    return df


def _load_csv(filename: str, parse_dates: tuple[str, ...]) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, filename)
    return _read_csv(path, parse_dates, os.path.getmtime(path))


def load_comercial() -> pd.DataFrame:
    return _load_csv("comercial.csv", ("fecha",))


def load_finanzas() -> pd.DataFrame:
    return _load_csv("finanzas.csv", ("fecha", "vencimiento"))


def load_costos() -> pd.DataFrame:
    return _load_csv("costos.csv", ("fecha",))


def load_contexto() -> pd.DataFrame:
    return _load_csv("contexto.csv", ("fecha",))


def load_campo() -> pd.DataFrame:
    return _load_csv("campo.csv", ("fecha",))


def load_empaque() -> pd.DataFrame:
    return _load_csv("empaque.csv", ("fecha",))
