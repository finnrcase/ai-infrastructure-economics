"""Process stored AEO2026 power outlook series for the dashboard.

Version 1 intentionally uses a local AEO2026.zip file instead of live EIA API
requests. The script extracts the national electricity-use and planned-capacity
series needed by the Streamlit dashboard and writes clean CSV outputs.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_ZIP = PROJECT_ROOT / "data" / "raw" / "AEO2026.zip"
PROCESSED_OUTPUT = PROJECT_ROOT / "data" / "processed" / "aeo2026_power_outlook.csv"
DASHBOARD_OUTPUT = PROJECT_ROOT / "outputs" / "tables" / "national_power_outlook_2030.csv"

# National baseline values documented in Notebook 7 from EIA electricity data.
CURRENT_US_CAPACITY_MW = 1_230_416
CURRENT_US_RETAIL_SALES_MWH = 3_975_381_832

SCENARIOS = {
    "Low": "LM2026",
    "Baseline": "CB2026",
    "High": "HIGHELDMD",
}

SERIES_SUFFIXES = {
    "total_electricity_use_bkwh": "CNSM_NA_ELEP_NA_TEL_NA_USA_BLNKWH",
    "planned_capacity_additions_gw": "CAP_NA_ELEP_CPA_NA_NA_NA_GW",
}


def _series_year_value(series: dict, year: int) -> float:
    values = {int(item[0]): item[1] for item in series["data"]}
    return float(values[year])


def load_aeo_series() -> dict[tuple[str, str], dict]:
    if not RAW_ZIP.exists():
        raise FileNotFoundError(
            f"Missing {RAW_ZIP}. Place the downloaded AEO2026.zip in data/raw/."
        )

    selected = {}
    wanted_codes = set(SCENARIOS.values())

    with zipfile.ZipFile(RAW_ZIP) as archive:
        with archive.open("AEO2026.txt") as file_obj:
            for raw_line in file_obj:
                series = json.loads(raw_line)
                series_id = series.get("series_id")
                if not series_id:
                    continue

                parts = series_id.split(".")
                if len(parts) < 3:
                    continue

                scenario_code = parts[2]
                if scenario_code not in wanted_codes:
                    continue

                for metric_name, suffix in SERIES_SUFFIXES.items():
                    if suffix in series_id:
                        selected[(scenario_code, metric_name)] = series

    missing = [
        (scenario_code, metric_name)
        for scenario_code in wanted_codes
        for metric_name in SERIES_SUFFIXES
        if (scenario_code, metric_name) not in selected
    ]
    if missing:
        raise ValueError(f"Missing expected AEO2026 series: {missing}")

    return selected


def build_power_outlook() -> pd.DataFrame:
    aeo_series = load_aeo_series()
    rows = []

    for scenario, scenario_code in SCENARIOS.items():
        demand_series = aeo_series[
            (scenario_code, "total_electricity_use_bkwh")
        ]
        capacity_series = aeo_series[
            (scenario_code, "planned_capacity_additions_gw")
        ]

        aeo_2025_demand_mwh = (
            _series_year_value(demand_series, 2025) * 1_000_000
        )
        projected_2030_demand_mwh = (
            _series_year_value(demand_series, 2030) * 1_000_000
        )
        planned_capacity_additions_mw = (
            _series_year_value(capacity_series, 2030) * 1_000
        )

        rows.append(
            {
                "scenario": scenario,
                "aeo_scenario_code": scenario_code,
                "demand_growth_percent": (
                    (
                        projected_2030_demand_mwh
                        / CURRENT_US_RETAIL_SALES_MWH
                        - 1
                    )
                    * 100
                ),
                "capacity_realization_percent": 100.0,
                "current_demand_mwh": CURRENT_US_RETAIL_SALES_MWH,
                "aeo_2025_total_electricity_use_mwh": aeo_2025_demand_mwh,
                "projected_2030_demand_mwh": projected_2030_demand_mwh,
                "demand_growth_mwh": (
                    projected_2030_demand_mwh - CURRENT_US_RETAIL_SALES_MWH
                ),
                "current_capacity_mw": CURRENT_US_CAPACITY_MW,
                "planned_capacity_additions_mw": planned_capacity_additions_mw,
                "realized_capacity_additions_mw": planned_capacity_additions_mw,
                "projected_2030_capacity_mw": (
                    CURRENT_US_CAPACITY_MW + planned_capacity_additions_mw
                ),
                "capacity_growth_mw": planned_capacity_additions_mw,
                "aeo_demand_series_id": demand_series["series_id"],
                "aeo_capacity_additions_series_id": capacity_series["series_id"],
                "source_dataset": "EIA Annual Energy Outlook 2026",
                "source_file": "data/raw/AEO2026.zip",
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    power_outlook = build_power_outlook()
    PROCESSED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    power_outlook.to_csv(PROCESSED_OUTPUT, index=False)
    power_outlook.to_csv(DASHBOARD_OUTPUT, index=False)
    print(f"Wrote {PROCESSED_OUTPUT}")
    print(f"Wrote {DASHBOARD_OUTPUT}")


if __name__ == "__main__":
    main()
