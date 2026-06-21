"""Optional EIA API helpers for live electricity data.

The dashboard must continue to work without an API key. These helpers read the
key only from EIA_API_KEY, cache successful API responses as local CSV files,
and fall back to the cached CSV whenever live data is unavailable.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
    / "eia_generating_capacity_by_state_source.csv"
)
EIA_CAPABILITY_ENDPOINT = (
    "https://api.eia.gov/v2/electricity/"
    "state-electricity-profiles/capability/data/"
)


def get_eia_api_key() -> str | None:
    """Return the EIA API key from the process environment, if available."""
    api_key = os.getenv("EIA_API_KEY")
    if not api_key:
        return None
    return api_key.strip() or None


def _request_eia_page(
    api_key: str,
    data_field: str,
    offset: int,
    length: int,
) -> dict:
    params = [
        ("api_key", api_key),
        ("frequency", "annual"),
        ("data[0]", data_field),
        ("start", "2020"),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "desc"),
        ("offset", str(offset)),
        ("length", str(length)),
    ]
    url = f"{EIA_CAPABILITY_ENDPOINT}?{urlencode(params)}"

    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_state_generating_capacity(api_key: str) -> dict:
    """Fetch state generating capacity by energy source from EIA v2.

    EIA's capability route has historically exposed the numeric value as
    "capability". A fallback to "capacity" keeps this helper resilient if the
    field label differs in the API response.
    """
    if not api_key:
        raise ValueError("EIA_API_KEY is missing.")

    last_error = None
    for data_field in ["capability", "capacity"]:
        all_records = []
        try:
            offset = 0
            page_length = 5000
            total = None

            while True:
                raw_page = _request_eia_page(
                    api_key=api_key,
                    data_field=data_field,
                    offset=offset,
                    length=page_length,
                )
                response = raw_page.get("response", {})
                page_records = response.get("data", [])
                total = response.get("total", total)
                all_records.extend(page_records)

                offset += page_length
                if not page_records or total is None or offset >= int(total):
                    break

            return {
                "data_field": data_field,
                "response": {
                    "data": all_records,
                    "total": len(all_records),
                },
            }
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            last_error = exc

    raise RuntimeError(f"EIA API request failed: {last_error}") from last_error


def _first_available(row: pd.Series, candidates: list[str]):
    for candidate in candidates:
        if candidate in row and pd.notna(row[candidate]):
            return row[candidate]
    return None


def process_generating_capacity(raw_data: dict) -> pd.DataFrame:
    """Normalize EIA API records into state/source/year capacity rows."""
    records = raw_data.get("response", {}).get("data", [])
    if not records:
        return pd.DataFrame(
            columns=[
                "period",
                "state",
                "state_id",
                "energy_source",
                "energy_source_description",
                "generating_capacity_mw",
                "units",
                "retrieved_at_utc",
            ]
        )

    df = pd.DataFrame(records)
    data_field = raw_data.get("data_field", "capability")

    rows = []
    retrieved_at = datetime.now(timezone.utc).isoformat()

    for _, row in df.iterrows():
        capacity_value = _first_available(
            row,
            [
                data_field,
                "capability",
                "capacity",
                "value",
            ],
        )
        if capacity_value is None:
            continue

        rows.append(
            {
                "period": _first_available(row, ["period", "year"]),
                "state": _first_available(
                    row,
                    [
                        "stateDescription",
                        "state-description",
                        "stateName",
                        "state",
                    ],
                ),
                "state_id": _first_available(
                    row,
                    [
                        "stateId",
                        "stateid",
                        "state-id",
                    ],
                ),
                "energy_source": _first_available(
                    row,
                    [
                        "energySource",
                        "energysourceid",
                        "energy-source",
                        "source",
                    ],
                ),
                "energy_source_description": _first_available(
                    row,
                    [
                        "energySourceDescription",
                        "energy-source-description",
                        "sourceDescription",
                    ],
                ),
                "generating_capacity_mw": pd.to_numeric(
                    capacity_value,
                    errors="coerce",
                ),
                "units": _first_available(
                    row,
                    [
                        f"{data_field}-units",
                        "capability-units",
                        "capacity-units",
                        "units",
                    ],
                ),
                "retrieved_at_utc": retrieved_at,
            }
        )

    processed = pd.DataFrame(rows)
    if processed.empty:
        return processed

    processed["period"] = pd.to_numeric(
        processed["period"],
        errors="coerce",
    ).astype("Int64")
    processed = processed.dropna(subset=["period", "generating_capacity_mw"])
    processed = processed[
        processed["energy_source_description"].fillna("") != "All"
    ]

    group_cols = [
        "period",
        "state",
        "state_id",
        "energy_source",
        "energy_source_description",
        "units",
        "retrieved_at_utc",
    ]
    processed = (
        processed
        .groupby(group_cols, as_index=False, dropna=False)[
            "generating_capacity_mw"
        ]
        .sum()
    )

    sort_cols = [
        col
        for col in [
            "period",
            "state",
            "energy_source_description",
            "energy_source",
        ]
        if col in processed.columns
    ]
    processed = processed.sort_values(
        sort_cols,
        ascending=[False] + [True] * (len(sort_cols) - 1),
    )

    return processed.reset_index(drop=True)


def _load_cached_capacity() -> pd.DataFrame | None:
    if not CACHE_PATH.exists():
        return None
    return pd.read_csv(CACHE_PATH)


def load_generating_capacity(use_api: bool = True) -> tuple[pd.DataFrame | None, dict]:
    """Load live EIA capacity data if possible, otherwise use local cache."""
    status = {
        "source": "unavailable",
        "message": "EIA generating capacity data is unavailable.",
        "cache_path": str(CACHE_PATH.relative_to(PROJECT_ROOT)),
    }

    api_key = get_eia_api_key()
    if use_api and api_key:
        try:
            raw_data = fetch_state_generating_capacity(api_key)
            processed = process_generating_capacity(raw_data)
            if not processed.empty:
                CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
                processed.to_csv(CACHE_PATH, index=False)
                status.update(
                    {
                        "source": "api",
                        "message": "Live EIA data enabled.",
                        "rows": len(processed),
                    }
                )
                return processed, status
        except Exception as exc:  # Keep dashboard resilient to API drift/outages.
            status.update(
                {
                    "source": "api_failed",
                    "message": f"Live EIA request failed; using cache if available. {exc}",
                }
            )

    cached = _load_cached_capacity()
    if cached is not None:
        status.update(
            {
                "source": "cache",
                "message": (
                    "Using local cached EIA generating capacity data."
                    if api_key
                    else "EIA_API_KEY missing; using local cached data."
                ),
                "rows": len(cached),
            }
        )
        return cached, status

    if not api_key:
        status.update(
            {
                "source": "local",
                "message": "EIA_API_KEY missing; dashboard is using local CSV files.",
                "rows": 0,
            }
        )

    return None, status
