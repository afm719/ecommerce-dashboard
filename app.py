"""Plug & Play E-commerce Analytics Dashboard (Shopify / WooCommerce).

Run with:  streamlit run app.py

The data layer is made of pure functions (no Streamlit calls) so it can be
tested in isolation. The UI lives in ``main()``.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

DUMMY_PATH: Path = Path(__file__).resolve().parent / "dummy_data.csv"

COLUMNS: list[str] = [
    "Fecha",
    "ID_Pedido",
    "Region",
    "Ventas_Brutas",
    "Devoluciones",
    "CAC",
    "Estado_Pedido",
]
CRITICAL_COLUMNS: list[str] = ["Fecha", "Ventas_Brutas"]

# Canonical status values.
COMPLETED, PENDING, CANCELLED, OTHER = "Completado", "Pendiente", "Cancelado", "Otro"
STATUS_ORDER: list[str] = [COMPLETED, PENDING, CANCELLED, OTHER]

# Fixed status colours (good / warning / critical / neutral), readable on
# both light and dark backgrounds.
STATUS_COLORS: dict[str, str] = {
    COMPLETED: "#0ca30c",
    PENDING: "#fab219",
    CANCELLED: "#d03b3b",
    OTHER: "#898781",
}
NET_COLOR = "#2a78d6"  # blue: net revenue
REFUND_COLOR = "#eb6834"  # orange: refunds

DEFAULT_REGION = "N/A"

# Accepted header aliases, in priority order (normalised: lowercase,
# no accents, non-alphanumerics collapsed to "_").
COLUMN_ALIASES: dict[str, list[str]] = {
    "Fecha": [
        "fecha", "date", "order_date", "created_at", "date_created",
        "created", "fecha_pedido", "fecha_de_pedido", "paid_at",
        "processed_at", "order_created", "purchase_date", "day",
    ],
    "ID_Pedido": [
        "id_pedido", "order_id", "order_number", "order_no", "order",
        "name", "id", "number", "pedido", "numero_pedido", "n_pedido",
    ],
    "Region": [
        "region", "country", "shipping_country", "billing_country",
        "country_code", "shipping_country_code", "billing_country_code",
        "pais", "market", "zona", "state", "province",
    ],
    "Ventas_Brutas": [
        "ventas_brutas", "total", "order_total", "gross_sales", "total_sales",
        "sales", "revenue", "amount", "total_price", "grand_total",
        "order_total_amount", "subtotal", "importe", "ventas", "total_pedido",
    ],
    "Devoluciones": [
        "devoluciones", "refunds", "refunded", "refund", "refund_amount",
        "refunded_amount", "total_refunded", "amount_refunded",
        "order_refund", "returns", "reembolsos", "reembolso",
    ],
    "CAC": [
        "cac", "customer_acquisition_cost", "acquisition_cost", "cpa",
        "ad_spend", "marketing_cost", "coste_adquisicion", "costo_adquisicion",
    ],
    "Estado_Pedido": [
        "estado_pedido", "status", "order_status", "estado",
        "financial_status", "payment_status", "estado_del_pedido",
    ],
}

# Raw status keywords (normalised, "wc-" prefix removed) -> canonical status.
STATUS_MAP: dict[str, str] = {
    **dict.fromkeys(
        [
            "completed", "complete", "completado", "completada", "paid",
            "pagado", "pagada", "fulfilled", "delivered", "entregado",
            "entregada", "shipped", "enviado", "enviada", "success",
            "successful", "closed", "cerrado", "refunded", "reembolsado",
            "partially refunded", "parcialmente reembolsado", "devuelto",
        ],
        COMPLETED,
    ),
    **dict.fromkeys(
        [
            "pending", "pendiente", "processing", "procesando", "en proceso",
            "on hold", "en espera", "pending payment", "pago pendiente",
            "authorized", "autorizado", "partially paid", "unfulfilled",
            "awaiting", "awaiting payment", "open", "abierto",
        ],
        PENDING,
    ),
    **dict.fromkeys(
        [
            "cancelled", "canceled", "cancelado", "cancelada", "anulado",
            "anulada", "voided", "void", "failed", "fallido", "fallida",
            "rejected", "rechazado", "declined", "trash", "expired",
        ],
        CANCELLED,
    ),
}

CURRENCIES: dict[str, str] = {"€ EUR": "€", "$ USD": "$", "£ GBP": "£"}

# --------------------------------------------------------------------------- #
# Translations
# --------------------------------------------------------------------------- #

TEXTS: dict[str, dict[str, str]] = {
    "EN": {
        "title": "📊 E-commerce Analytics Dashboard",
        "subtitle": "Upload your Shopify or WooCommerce export and get instant insights. "
        "Your data never leaves your computer.",
        "language": "Language / Idioma",
        "data": "Data",
        "upload": "Upload your orders CSV",
        "upload_help": "Columns: Fecha, ID_Pedido, Region, Ventas_Brutas, Devoluciones, "
        "CAC, Estado_Pedido (English Shopify/WooCommerce names also work).",
        "template": "⬇️ Download CSV template",
        "filters": "Filters",
        "date_range": "Date range",
        "regions": "Regions",
        "statuses": "Order status",
        "currency": "Currency",
        "demo_mode": "**Demo Mode** — you are viewing sample data. Upload your own CSV in "
        "the sidebar to analyse your store.",
        "demo_memory": "**Demo Mode** — `dummy_data.csv` was not found or is unreadable, so "
        "a built-in sample dataset is shown.",
        "file_loaded": "✅ Loaded **{name}** — {rows} orders.",
        "upload_failed": "Could not use **{name}**: {reason} Showing demo data instead.",
        "err_empty": "the file is empty.",
        "err_unreadable": "the file could not be read as a CSV.",
        "err_missing": "required column(s) missing: {cols}.",
        "err_no_rows": "no row has a valid date and sales amount.",
        "err_unknown": "unexpected error ({detail}).",
        "warn_missing": "Optional column(s) not found: **{cols}**. Default values were used.",
        "warn_dropped": "{n} row(s) skipped because the date or sales amount was invalid.",
        "no_data": "No orders match the current filters. Adjust the filters in the sidebar.",
        "kpi_net": "Net Revenue",
        "kpi_net_help": "Gross sales minus refunds, excluding cancelled orders.",
        "kpi_cac": "Avg. CAC",
        "kpi_cac_help": "Average customer acquisition cost. Orders with CAC = 0 "
        "(organic/unknown) are ignored.",
        "kpi_return": "Return Rate",
        "kpi_return_help": "Refunds ÷ gross sales, excluding cancelled orders.",
        "kpi_aov": "Average Order Value",
        "kpi_aov_help": "Gross sales ÷ number of non-cancelled orders.",
        "chart_trend": "Monthly net revenue vs refunds",
        "chart_status": "Orders by status",
        "chart_region": "Net revenue by region",
        "net": "Net revenue",
        "refunds": "Refunds",
        "orders": "orders",
        "table": "🔎 View filtered data",
        "download": "⬇️ Download filtered data (CSV)",
        "fatal": "Something went wrong while building the dashboard. "
        "Please check your file and try again.",
        COMPLETED: "Completed",
        PENDING: "Pending",
        CANCELLED: "Cancelled",
        OTHER: "Other",
    },
    "ES": {
        "title": "📊 Dashboard Analítico E-commerce",
        "subtitle": "Sube la exportación de Shopify o WooCommerce y obtén información al "
        "instante. Tus datos nunca salen de tu ordenador.",
        "language": "Language / Idioma",
        "data": "Datos",
        "upload": "Sube el CSV de pedidos",
        "upload_help": "Columnas: Fecha, ID_Pedido, Region, Ventas_Brutas, Devoluciones, "
        "CAC, Estado_Pedido (también se aceptan los nombres en inglés de "
        "Shopify/WooCommerce).",
        "template": "⬇️ Descargar plantilla CSV",
        "filters": "Filtros",
        "date_range": "Rango de fechas",
        "regions": "Regiones",
        "statuses": "Estado del pedido",
        "currency": "Moneda",
        "demo_mode": "**Modo Demo** — estás viendo datos de ejemplo. Sube tu propio CSV "
        "en la barra lateral para analizar tu tienda.",
        "demo_memory": "**Modo Demo** — no se encontró `dummy_data.csv` o está dañado; se "
        "muestra un conjunto de ejemplo integrado.",
        "file_loaded": "✅ Cargado **{name}** — {rows} pedidos.",
        "upload_failed": "No se pudo usar **{name}**: {reason} Se muestran datos de demo.",
        "err_empty": "el archivo está vacío.",
        "err_unreadable": "el archivo no se pudo leer como CSV.",
        "err_missing": "faltan columnas obligatorias: {cols}.",
        "err_no_rows": "ninguna fila tiene una fecha y un importe de ventas válidos.",
        "err_unknown": "error inesperado ({detail}).",
        "warn_missing": "No se encontraron las columnas opcionales: **{cols}**. Se usaron "
        "valores por defecto.",
        "warn_dropped": "Se omitieron {n} fila(s) por fecha o importe de ventas no válidos.",
        "no_data": "Ningún pedido coincide con los filtros. Ajusta los filtros de la barra "
        "lateral.",
        "kpi_net": "Ingresos Netos",
        "kpi_net_help": "Ventas brutas menos devoluciones, sin pedidos cancelados.",
        "kpi_cac": "CAC Promedio",
        "kpi_cac_help": "Coste medio de adquisición de cliente. Se ignoran los pedidos "
        "con CAC = 0 (orgánicos/desconocidos).",
        "kpi_return": "Tasa de Devolución",
        "kpi_return_help": "Devoluciones ÷ ventas brutas, sin pedidos cancelados.",
        "kpi_aov": "Ticket Medio",
        "kpi_aov_help": "Ventas brutas ÷ número de pedidos no cancelados.",
        "chart_trend": "Ingresos netos vs devoluciones por mes",
        "chart_status": "Pedidos por estado",
        "chart_region": "Ingresos netos por región",
        "net": "Ingresos netos",
        "refunds": "Devoluciones",
        "orders": "pedidos",
        "table": "🔎 Ver datos filtrados",
        "download": "⬇️ Descargar datos filtrados (CSV)",
        "fatal": "Algo salió mal al construir el dashboard. Revisa tu archivo e "
        "inténtalo de nuevo.",
        COMPLETED: "Completado",
        PENDING: "Pendiente",
        CANCELLED: "Cancelado",
        OTHER: "Otro",
    },
}


class DataError(ValueError):
    """Raised when a CSV cannot be turned into a usable dataset.

    ``code`` is a key of ``TEXTS`` so the UI can show a translated reason.
    """

    def __init__(self, code: str, **params: Any) -> None:
        super().__init__(code)
        self.code = code
        self.params = params


# --------------------------------------------------------------------------- #
# Parsing helpers (pure functions)
# --------------------------------------------------------------------------- #


def normalize_header(name: Any) -> str:
    """Lowercase, strip accents and collapse non-alphanumerics to '_'."""
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def map_columns(columns: list[str]) -> dict[str, str]:
    """Return {original_column: canonical_column} for recognised headers."""
    normalized = {col: normalize_header(col) for col in columns}
    mapping: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            match = next(
                (c for c, n in normalized.items() if n == alias and c not in mapping),
                None,
            )
            if match is not None:
                mapping[match] = canonical
                break
    return mapping


def _clean_number_text(value: Any) -> str:
    """Keep only digits, separators and sign markers."""
    return re.sub(r"[^0-9,.\-()]", "", str(value))


def _decimal_vote(text: str) -> str | None:
    """Guess the decimal separator of a single cleaned number string."""
    if "," in text and "." in text:
        return "," if text.rfind(",") > text.rfind(".") else "."
    for sep, other in ((",", "."), (".", ",")):
        if sep in text:
            if text.count(sep) > 1:
                return other  # repeated separator => thousands
            if re.search(rf"\{sep}\d{{1,2}}$", text):
                return sep  # 1-2 trailing digits => decimal
    return None


def infer_decimal_separator(values: pd.Series) -> str | None:
    """Infer the decimal separator used across a column (',' / '.' / None)."""
    votes = [_decimal_vote(_clean_number_text(v)) for v in values.dropna().astype(str)]
    commas, dots = votes.count(","), votes.count(".")
    if commas == dots:
        return None
    return "," if commas > dots else "."


def parse_number(value: Any, decimal: str | None = None) -> float:
    """Parse '1.234,56', '1,234.56', '€ 12,50', '(5.00)', '$-3' ... into a float.

    ``decimal`` forces the decimal separator; when None it is guessed per value.
    Returns NaN when the value cannot be parsed.
    """
    if value is None:
        return float("nan")
    if isinstance(value, (int, float, np.number)) and not isinstance(value, bool):
        return float(value)
    raw = str(value).strip()
    text = _clean_number_text(raw)
    negative = "-" in text or (text.startswith("(") and text.endswith(")"))
    text = text.replace("-", "").replace("(", "").replace(")", "")
    if not re.search(r"\d", text):
        return float("nan")

    if decimal is None:
        # Ambiguous single separator + 3 digits defaults to US style:
        # "1,234" => 1234 and "0.125" => 0.125.
        decimal = _decimal_vote(text) or "."
    thousands = "." if decimal == "," else ","
    text = text.replace(thousands, "").replace(decimal, ".")
    if text.count(".") > 1:
        return float("nan")
    try:
        number = float(text)
    except ValueError:
        return float("nan")
    return -number if negative else number


def parse_number_series(values: pd.Series) -> pd.Series:
    """Vector version of ``parse_number`` with column-level separator inference."""
    if pd.api.types.is_numeric_dtype(values):
        return pd.to_numeric(values, errors="coerce").astype(float)
    decimal = infer_decimal_separator(values)
    return values.map(lambda v: parse_number(v, decimal)).astype(float)


_TZ_SUFFIX = re.compile(
    r"(\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?)\s*(?:Z|UTC|GMT|[+-]\d{2}:?\d{2})?\s*$",
    flags=re.IGNORECASE,
)
_DMY = re.compile(r"^\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})\b")


def parse_dates(values: pd.Series) -> pd.Series:
    """Parse ISO (with/without time & timezone) and dd/mm/yyyy dates.

    Timezone offsets are dropped so the store's local wall time is kept.
    Returns a day-normalised, tz-naive datetime64 Series (NaT when invalid).
    """
    if pd.api.types.is_datetime64_any_dtype(values):
        out = pd.to_datetime(values, errors="coerce")
        if getattr(out.dt, "tz", None) is not None:
            out = out.dt.tz_localize(None)
        return out.dt.normalize()

    text = values.astype("string").fillna("").str.strip()
    text = text.str.replace(_TZ_SUFFIX, r"\1", regex=True)
    result = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")

    # ISO-like: 2026-01-31, 2026/01/31, 2026-01-31T10:00:00
    iso_mask = text.str.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}")
    if iso_mask.any():
        iso = text[iso_mask].str.replace("/", "-", regex=False)
        result[iso_mask] = pd.to_datetime(iso, format="ISO8601", errors="coerce")

    # Day-first: 31/01/2026, 31-01-26, 31.01.2026 (month-first if day <= 12
    # everywhere and some "month" > 12, i.e. a US export).
    parts = text[~iso_mask].str.extract(_DMY)
    parts = parts.dropna()
    if not parts.empty:
        first, second, year = (parts[i].astype(int) for i in range(3))
        year = year.where(year >= 100, year + 2000)
        month_first = bool((second > 12).any() and not (first > 12).any())
        day, month = (second, first) if month_first else (first, second)
        result[parts.index] = pd.to_datetime(
            pd.DataFrame({"year": year, "month": month, "day": day}), errors="coerce"
        )

    # Last resort for anything else (e.g. "Jan 5, 2026").
    rest = result.isna() & text.ne("")
    if rest.any():
        try:
            result[rest] = pd.to_datetime(text[rest], format="mixed", errors="coerce")
        except (ValueError, TypeError, OverflowError):
            pass
    return result.dt.normalize()


def normalize_status(value: Any) -> str:
    """Map raw status text (EN/ES, Shopify/WooCommerce, 'wc-' prefix) to canonical."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return OTHER
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    text = text.strip().lower()
    text = re.sub(r"^wc-", "", text)
    text = re.sub(r"[_\-]+", " ", text).strip()
    return STATUS_MAP.get(text, OTHER)


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #


def decode_bytes(data: bytes) -> str:
    """Decode with utf-8-sig, cp1252, latin-1 (latin-1 never fails)."""
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def detect_separator(text: str) -> str:
    """Pick ';', ',' or tab from the header line (quotes respected)."""
    header = next((line for line in text.splitlines() if line.strip()), "")
    counts: dict[str, int] = {}
    for sep in (",", ";", "\t"):
        try:
            counts[sep] = len(next(csv.reader([header], delimiter=sep)))
        except (csv.Error, StopIteration):
            counts[sep] = 0
    best = max(counts, key=lambda s: counts[s])
    return best if counts[best] > 1 else ","


def standardize_dataframe(raw: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, dict]]]:
    """Rename, parse and clean a raw string DataFrame into the canonical schema.

    Returns (clean_df, warnings) where warnings are (TEXTS key, params) tuples.
    Raises DataError when critical columns are missing or no row is valid.
    """
    warnings: list[tuple[str, dict]] = []
    raw = raw.loc[:, [c for c in raw.columns if not str(c).startswith("Unnamed")]]
    mapping = map_columns([str(c) for c in raw.columns])
    df = raw.rename(columns={c: mapping[str(c)] for c in raw.columns if str(c) in mapping})
    df = df.loc[:, [c for c in COLUMNS if c in df.columns]].copy()

    missing_critical = [c for c in CRITICAL_COLUMNS if c not in df.columns]
    if missing_critical:
        raise DataError("err_missing", cols=", ".join(missing_critical))

    missing_optional = [c for c in COLUMNS if c not in df.columns]
    if missing_optional:
        warnings.append(("warn_missing", {"cols": ", ".join(missing_optional)}))

    df["Fecha"] = parse_dates(df["Fecha"])
    df["Ventas_Brutas"] = parse_number_series(df["Ventas_Brutas"])
    valid = df["Fecha"].notna() & df["Ventas_Brutas"].notna()
    dropped = int((~valid).sum())
    df = df.loc[valid].reset_index(drop=True)
    if df.empty:
        raise DataError("err_no_rows")
    if dropped:
        warnings.append(("warn_dropped", {"n": dropped}))

    # Negative gross sales (refund lines) are treated as 0 sales.
    df["Ventas_Brutas"] = df["Ventas_Brutas"].clip(lower=0)

    if "ID_Pedido" in df:
        ids = df["ID_Pedido"].astype("string").fillna("").str.strip()
        auto = pd.Series([f"AUTO-{i + 1:05d}" for i in range(len(df))])
        df["ID_Pedido"] = ids.where(ids.ne(""), auto)
    else:
        df["ID_Pedido"] = [f"AUTO-{i + 1:05d}" for i in range(len(df))]

    if "Region" in df:
        region = df["Region"].astype("string").fillna("").str.strip()
        df["Region"] = region.where(region.ne(""), DEFAULT_REGION)
    else:
        df["Region"] = DEFAULT_REGION

    for col in ("Devoluciones", "CAC"):
        if col in df:
            df[col] = parse_number_series(df[col]).fillna(0.0).abs()
        else:
            df[col] = 0.0
    # Refunds can never exceed the gross amount of the order.
    df["Devoluciones"] = np.minimum(df["Devoluciones"], df["Ventas_Brutas"])

    if "Estado_Pedido" in df:
        df["Estado_Pedido"] = df["Estado_Pedido"].map(normalize_status)
    else:
        df["Estado_Pedido"] = COMPLETED

    df["ID_Pedido"] = df["ID_Pedido"].astype(str)
    df["Region"] = df["Region"].astype(str)
    return df.loc[:, COLUMNS].sort_values("Fecha").reset_index(drop=True), warnings


def parse_csv_bytes(data: bytes) -> tuple[pd.DataFrame, list[tuple[str, dict]]]:
    """Read CSV bytes robustly and return the canonical DataFrame + warnings."""
    if not data or not data.strip():
        raise DataError("err_empty")
    text = decode_bytes(data)
    if not text.strip():
        raise DataError("err_empty")
    try:
        raw = pd.read_csv(
            io.StringIO(text),
            sep=detect_separator(text),
            dtype=str,
            keep_default_na=False,
            skipinitialspace=True,
            skip_blank_lines=True,
            on_bad_lines="skip",
            engine="python",
        )
    except pd.errors.EmptyDataError as exc:
        raise DataError("err_empty") from exc
    except (pd.errors.ParserError, csv.Error, ValueError) as exc:
        raise DataError("err_unreadable") from exc
    raw.columns = [str(c).strip() for c in raw.columns]
    if raw.empty:
        raise DataError("err_no_rows")
    return standardize_dataframe(raw)


@st.cache_data(show_spinner=False)
def load_csv_bytes(data: bytes) -> tuple[pd.DataFrame, list[tuple[str, dict]]]:
    """Cached wrapper around ``parse_csv_bytes``."""
    return parse_csv_bytes(data)


def build_demo_dataframe(n_orders: int = 60, seed: int = 7) -> pd.DataFrame:
    """Generate a coherent in-memory demo dataset (fallback for a missing file)."""
    rng = np.random.default_rng(seed)
    regions = ["España", "France", "Deutschland", "Italia", "Portugal"]
    dates = pd.Timestamp("2026-01-01") + pd.to_timedelta(
        np.sort(rng.integers(0, 181, n_orders)), unit="D"
    )
    sales = np.round(rng.uniform(60, 520, n_orders), 2)
    status = rng.choice(
        [COMPLETED, PENDING, CANCELLED], size=n_orders, p=[0.8, 0.12, 0.08]
    )
    refund_share = np.where(rng.random(n_orders) < 0.2, rng.uniform(0.1, 1.0, n_orders), 0)
    refunds = np.round(sales * refund_share, 2)
    refunds = np.where(status == CANCELLED, 0.0, refunds)
    cac = np.where(rng.random(n_orders) < 0.15, 0.0, np.round(rng.uniform(8, 40, n_orders), 2))
    return pd.DataFrame(
        {
            "Fecha": dates,
            "ID_Pedido": [f"DEMO-{1001 + i}" for i in range(n_orders)],
            "Region": rng.choice(regions, size=n_orders),
            "Ventas_Brutas": sales,
            "Devoluciones": refunds,
            "CAC": cac,
            "Estado_Pedido": status,
        }
    )


def load_demo() -> tuple[pd.DataFrame, str]:
    """Load ``dummy_data.csv``; fall back to generated data. Returns (df, source)."""
    try:
        df, _ = load_csv_bytes(DUMMY_PATH.read_bytes())
        return df, "demo_file"
    except Exception:  # noqa: BLE001 - any problem => in-memory demo
        return build_demo_dataframe(), "demo_memory"


def template_csv() -> bytes:
    """CSV template with the expected columns and two example rows."""
    example = pd.DataFrame(
        [
            ["2026-01-15", "ORD-1001", "España", 120.50, 0, 15.20, "Completado"],
            ["2026-01-16", "ORD-1002", "France", 89.90, 89.90, 12.00, "Completado"],
        ],
        columns=COLUMNS,
    )
    return example.to_csv(index=False).encode("utf-8-sig")


# --------------------------------------------------------------------------- #
# Metrics (pure functions)
# --------------------------------------------------------------------------- #


def safe_div(numerator: float, denominator: float) -> float:
    """Division that returns 0.0 instead of failing or returning inf/NaN."""
    if not denominator or pd.isna(denominator) or pd.isna(numerator):
        return 0.0
    return float(numerator) / float(denominator)


def compute_kpis(df: pd.DataFrame) -> dict[str, float]:
    """Net revenue, average CAC, return rate (%) and average order value."""
    active = df[df["Estado_Pedido"] != CANCELLED]
    gross = float(active["Ventas_Brutas"].sum())
    refunds = float(active["Devoluciones"].sum())
    cac = df.loc[df["CAC"] > 0, "CAC"]
    return {
        "net_revenue": gross - refunds,
        "avg_cac": float(cac.mean()) if not cac.empty else 0.0,
        "return_rate": safe_div(refunds, gross) * 100,
        "aov": safe_div(gross, len(active)),
    }


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly net revenue and refunds (cancelled orders excluded)."""
    active = df[df["Estado_Pedido"] != CANCELLED].copy()
    active["Neto"] = active["Ventas_Brutas"] - active["Devoluciones"]
    active["Mes"] = active["Fecha"].dt.to_period("M").dt.to_timestamp()
    return (
        active.groupby("Mes", as_index=False)[["Neto", "Devoluciones"]]
        .sum()
        .sort_values("Mes")
    )


def region_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Net revenue per region, ascending (largest bar ends up on top)."""
    active = df[df["Estado_Pedido"] != CANCELLED].copy()
    active["Neto"] = active["Ventas_Brutas"] - active["Devoluciones"]
    return active.groupby("Region", as_index=False)["Neto"].sum().sort_values("Neto")


# --------------------------------------------------------------------------- #
# Formatting & charts
# --------------------------------------------------------------------------- #


def format_money(value: float, symbol: str, lang: str) -> str:
    """'€1,234.56' (EN) or '1.234,56 €' (ES)."""
    text = f"{value:,.2f}"
    if lang == "ES":
        text = text.replace(",", "§").replace(".", ",").replace("§", ".")
        return f"{text} {symbol}"
    return f"{symbol}{text}"


def format_pct(value: float, lang: str) -> str:
    text = f"{value:.1f}%"
    return text.replace(".", ",") if lang == "ES" else text


def _base_layout(fig: go.Figure, lang: str, height: int = 360) -> go.Figure:
    """Transparent, theme-neutral layout (Streamlit's theme supplies the ink)."""
    fig.update_layout(
        height=height,
        margin={"l": 8, "r": 8, "t": 16, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        separators=",." if lang == "ES" else ".,",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
    )
    return fig


def _money_hover(symbol: str, lang: str) -> str:
    return "%{y:,.2f} " + symbol if lang == "ES" else symbol + "%{y:,.2f}"


def trend_chart(df: pd.DataFrame, t: dict[str, str], symbol: str, lang: str) -> go.Figure:
    trend = monthly_trend(df)
    hover = _money_hover(symbol, lang)
    fig = go.Figure()
    for col, name, color in (
        ("Neto", t["net"], NET_COLOR),
        ("Devoluciones", t["refunds"], REFUND_COLOR),
    ):
        fig.add_trace(
            go.Scatter(
                x=trend["Mes"],
                y=trend[col],
                name=name,
                mode="lines+markers",
                line={"color": color, "width": 2},
                marker={"size": 8},
                fill="tozeroy",
                hovertemplate=hover,
            )
        )
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(dtick="M1", tickformat="%b %Y", showgrid=False)
    fig.update_yaxes(tickprefix="" if lang == "ES" else symbol,
                     ticksuffix=f" {symbol}" if lang == "ES" else "")
    return _base_layout(fig, lang)


def status_chart(df: pd.DataFrame, t: dict[str, str], lang: str) -> go.Figure:
    counts = df["Estado_Pedido"].value_counts()
    statuses = [s for s in STATUS_ORDER if counts.get(s, 0) > 0]
    fig = go.Figure(
        go.Pie(
            labels=[t[s] for s in statuses],
            values=[int(counts[s]) for s in statuses],
            hole=0.62,
            sort=False,
            direction="clockwise",
            marker={"colors": [STATUS_COLORS[s] for s in statuses]},
            textinfo="percent",
            hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
        )
    )
    fig.add_annotation(
        text=f"<b>{len(df)}</b><br>{t['orders']}",
        x=0.5, y=0.5, showarrow=False, font={"size": 20},
    )
    return _base_layout(fig, lang)


def region_chart(df: pd.DataFrame, t: dict[str, str], symbol: str, lang: str) -> go.Figure:
    data = region_revenue(df)
    labels = [format_money(v, symbol, lang) for v in data["Neto"]]
    fig = go.Figure(
        go.Bar(
            x=data["Neto"],
            y=data["Region"],
            orientation="h",
            marker={"color": NET_COLOR, "cornerradius": 4},
            text=labels,
            textposition="auto",
            customdata=labels,
            hovertemplate="%{y}: %{customdata}<extra></extra>",
            name=t["net"],
        )
    )
    fig.update_xaxes(showticklabels=False, showgrid=False)
    fig.update_layout(bargap=0.35)
    return _base_layout(fig, lang, height=max(260, 60 * len(data) + 60))


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #

CSS = """
<style>
div[data-testid="stMetric"] {
    background: rgba(128, 128, 128, 0.06);
    border: 1px solid rgba(128, 128, 128, 0.22);
    border-radius: 12px;
    padding: 16px 20px;
}
div[data-testid="stMetricValue"] { font-weight: 650; }
</style>
"""


def date_bounds(selection: Any, lo: date, hi: date) -> tuple[date, date]:
    """Normalise the date_input value (tuple of 0/1/2 dates or a date)."""
    if isinstance(selection, date):
        return selection, selection
    picked = [d for d in (selection or ()) if d is not None]
    if not picked:
        return lo, hi
    if len(picked) == 1:  # user has clicked only the start date so far
        return picked[0], picked[0]
    return min(picked), max(picked)


def main() -> None:
    st.set_page_config(
        page_title="E-commerce Analytics", page_icon="📊", layout="wide"
    )
    st.markdown(CSS, unsafe_allow_html=True)

    with st.sidebar:
        lang = st.radio("Language / Idioma", ["EN", "ES"], horizontal=True, key="lang")
    t = TEXTS[lang]

    try:
        render_dashboard(t, lang)
    except Exception as exc:  # noqa: BLE001 - never show a traceback
        st.error(t["fatal"])
        st.caption(f"{type(exc).__name__}: {exc}")


def render_dashboard(t: dict[str, str], lang: str) -> None:
    with st.sidebar:
        st.header(t["data"])
        uploaded = st.file_uploader(t["upload"], type=["csv"], help=t["upload_help"])
        st.download_button(
            t["template"],
            data=template_csv(),
            file_name="plantilla_pedidos.csv",
            mime="text/csv",
            width="stretch",
        )

    st.title(t["title"])
    st.caption(t["subtitle"])

    df: pd.DataFrame | None = None
    load_warnings: list[tuple[str, dict]] = []
    if uploaded is not None:
        try:
            df, load_warnings = load_csv_bytes(uploaded.getvalue())
            st.success(t["file_loaded"].format(name=uploaded.name, rows=len(df)))
        except DataError as exc:
            reason = t[exc.code].format(**exc.params)
            st.error(t["upload_failed"].format(name=uploaded.name, reason=reason))
        except Exception as exc:  # noqa: BLE001
            reason = t["err_unknown"].format(detail=type(exc).__name__)
            st.error(t["upload_failed"].format(name=uploaded.name, reason=reason))
    if df is None:
        df, source = load_demo()
        st.info(t[source if source == "demo_memory" else "demo_mode"], icon="🧪")
    for code, params in load_warnings:
        st.warning(t[code].format(**params))

    # ---- Filters -------------------------------------------------------- #
    min_day, max_day = df["Fecha"].min().date(), df["Fecha"].max().date()
    regions = sorted(df["Region"].unique().tolist())
    statuses = [s for s in STATUS_ORDER if s in set(df["Estado_Pedido"])]
    with st.sidebar:
        st.header(t["filters"])
        selection = st.date_input(
            t["date_range"],
            value=(min_day, max_day),
            min_value=min_day,
            max_value=max_day,
            format="DD/MM/YYYY" if lang == "ES" else "YYYY/MM/DD",
        )
        start, end = date_bounds(selection, min_day, max_day)
        chosen_regions = st.multiselect(t["regions"], regions, default=regions)
        chosen_status = st.multiselect(
            t["statuses"], statuses, default=statuses, format_func=lambda s: t[s]
        )
        currency = st.selectbox(t["currency"], list(CURRENCIES))
    symbol = CURRENCIES[currency]

    days = df["Fecha"].dt.date
    filtered = df[
        days.between(start, end)
        & df["Region"].isin(chosen_regions)
        & df["Estado_Pedido"].isin(chosen_status)
    ]
    if filtered.empty:
        st.warning(t["no_data"])
        st.stop()

    # ---- KPIs ------------------------------------------------------------ #
    kpis = compute_kpis(filtered)
    cols = st.columns(4)
    cols[0].metric(t["kpi_net"], format_money(kpis["net_revenue"], symbol, lang),
                   help=t["kpi_net_help"])
    cols[1].metric(t["kpi_cac"], format_money(kpis["avg_cac"], symbol, lang),
                   help=t["kpi_cac_help"])
    cols[2].metric(t["kpi_return"], format_pct(kpis["return_rate"], lang),
                   help=t["kpi_return_help"])
    cols[3].metric(t["kpi_aov"], format_money(kpis["aov"], symbol, lang),
                   help=t["kpi_aov_help"])

    # ---- Charts ---------------------------------------------------------- #
    st.subheader(t["chart_trend"])
    st.plotly_chart(trend_chart(filtered, t, symbol, lang), width="stretch")

    left, right = st.columns(2)
    with left:
        st.subheader(t["chart_status"])
        st.plotly_chart(status_chart(filtered, t, lang), width="stretch")
    with right:
        st.subheader(t["chart_region"])
        st.plotly_chart(region_chart(filtered, t, symbol, lang), width="stretch")

    # ---- Data table ------------------------------------------------------ #
    with st.expander(t["table"]):
        view = filtered.assign(Fecha=filtered["Fecha"].dt.strftime("%Y-%m-%d"))
        st.dataframe(view, width="stretch", hide_index=True)
        st.download_button(
            t["download"],
            data=view.to_csv(index=False).encode("utf-8-sig"),
            file_name="datos_filtrados.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
