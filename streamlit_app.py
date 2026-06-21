from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.eia_api import load_generating_capacity


PROJECT_ROOT = Path(__file__).resolve().parent
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
BTM_INPUTS_PATH = PROJECT_ROOT / "sources" / "btm_inputs.csv"


TABLES = {
    "competitiveness": "state_competitiveness_results.csv",
    "architecture": "architecture_results.csv",
    "winner_frequency": "monte_carlo_winner_frequency.csv",
    "community_tradeoff": "community_impact_tradeoff.csv",
    "mitigation_fund": "community_mitigation_fund.csv",
    "power_outlook": "national_power_outlook_2030.csv",
}


STATE_REGION = {
    "Arizona": "West",
    "California": "West",
    "Georgia": "South",
    "Illinois": "Midwest",
    "Indiana": "Midwest",
    "Nevada": "West",
    "North Carolina": "South",
    "Ohio": "Midwest",
    "Oregon": "West",
    "Pennsylvania": "Northeast",
    "Tennessee": "South",
    "Texas": "South",
    "Utah": "West",
    "Virginia": "South",
    "Washington": "West",
}


STATE_ABBR = {
    "Arizona": "AZ",
    "California": "CA",
    "Georgia": "GA",
    "Illinois": "IL",
    "Indiana": "IN",
    "Nevada": "NV",
    "North Carolina": "NC",
    "Ohio": "OH",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Virginia": "VA",
    "Washington": "WA",
}


ARCHITECTURE_DIVERSIFICATION_SCORE = {
    "Grid Only": 0.50,
    "Behind-the-Meter": 0.75,
    "Hybrid": 0.90,
}


st.set_page_config(
    page_title="AI Infrastructure Site Selection Dashboard",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
        max-width: 1220px;
    }
    [data-testid="stMetric"] {
        border-bottom: 1px solid rgba(49, 51, 63, 0.12);
        padding-bottom: 0.55rem;
    }
    [data-testid="stSidebar"] {
        background-color: #f3f5f8;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(49, 51, 63, 0.10);
        border-radius: 6px;
    }
    h1, h2, h3 {
        letter-spacing: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_csv(path: Path):
    """Load exported notebook outputs without mutating research artifacts."""
    if not path.exists():
        return None
    return pd.read_csv(path)


def load_tables():
    return {
        key: load_csv(TABLE_DIR / filename)
        for key, filename in TABLES.items()
    }


@st.cache_data(show_spinner=False, ttl=3600)
def load_optional_eia_capacity():
    """Load optional live/cached EIA capacity data without blocking the app."""
    return load_generating_capacity(use_api=True)


@st.cache_data(show_spinner=False)
def load_btm_inputs():
    """Load Notebook 5 BTM inputs, including NREL PVWatts solar factors."""
    return load_csv(BTM_INPUTS_PATH)


def format_number(value: float, prefix: str = "", suffix: str = "") -> str:
    if pd.isna(value):
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"{prefix}{value / 1_000_000_000:.1f}B{suffix}"
    if abs(value) >= 1_000_000:
        return f"{prefix}{value / 1_000_000:.1f}M{suffix}"
    if abs(value) >= 1_000:
        return f"{prefix}{value / 1_000:.1f}K{suffix}"
    return f"{prefix}{value:,.2f}{suffix}"


def require_table(df, filename: str) -> bool:
    if df is not None:
        return True
    st.info(
        f"`outputs/tables/{filename}` is not available yet. "
        "Run the corresponding research notebook to populate this section."
    )
    return False


def section_header(title: str, caption: str) -> None:
    st.subheader(title)
    st.caption(caption)


def add_region_column(df):
    if df is None or "State" not in df.columns:
        return df
    df = df.copy()
    df["Region"] = df["State"].map(STATE_REGION).fillna("Unmapped")
    return df


def apply_state_filters(df, selected_states, region_preference):
    if df is None or "State" not in df.columns:
        return df

    filtered = add_region_column(df)

    if region_preference != "No Preference":
        filtered = filtered[filtered["Region"] == region_preference]

    if selected_states:
        filtered = filtered[filtered["State"].isin(selected_states)]

    return filtered.copy()


def calculate_custom_decision_scores(df, priorities):
    if df is None:
        return df, {}

    score_columns = {
        "price_score": priorities["Cost"],
        "capacity_score": priorities["Reliability"],
        "renewable_score": priorities["Renewable"],
        "ecosystem_score": priorities["Ecosystem"],
        "interconnection_score": priorities["Interconnection"],
    }
    available_scores = {
        col: weight
        for col, weight in score_columns.items()
        if col in df.columns
    }
    total_weight = sum(available_scores.values())
    normalized_weights = (
        {
            col: weight / total_weight
            for col, weight in available_scores.items()
        }
        if total_weight
        else {}
    )

    scored = df.copy()
    if normalized_weights:
        scored["custom_decision_score"] = sum(
            scored[col] * weight
            for col, weight in normalized_weights.items()
        )
    else:
        scored["custom_decision_score"] = np.nan

    return scored, normalized_weights


def normalize_btm_mix(solar_pct, gas_pct, battery_other_pct):
    mix = {
        "Solar": float(solar_pct),
        "Natural Gas": float(gas_pct),
        "Battery / Other": float(battery_other_pct),
    }
    total = sum(mix.values())
    if total <= 0:
        return {key: 0 for key in mix}, total
    return {key: value / total for key, value in mix.items()}, total


def calculate_power_plan(
    df,
    power_strategy,
    compute_load_mw,
    normalized_btm_mix,
):
    if df is None:
        return None

    annual_energy_mwh = compute_load_mw * 8760
    results = df.copy()
    results["annual_energy_mwh"] = annual_energy_mwh

    grid_cost = results.get("grid_cost_usd_per_mwh")
    gas_cost = results.get("gas_cost_usd_per_mwh")
    solar_cost = results.get("solar_cost_usd_per_mwh")
    hybrid_cost = results.get("hybrid_cost_usd_per_mwh")

    if power_strategy == "Grid Only":
        results["recommended_architecture"] = "Grid Only"
        results["estimated_cost_usd_per_mwh"] = grid_cost
        results["power_mix_display"] = "Grid 100%"
    elif power_strategy == "Hybrid":
        results["recommended_architecture"] = "Hybrid"
        results["estimated_cost_usd_per_mwh"] = hybrid_cost
        results["power_mix_display"] = "Hybrid model"
    else:
        solar_share = normalized_btm_mix["Solar"]
        gas_share = normalized_btm_mix["Natural Gas"]
        battery_share = normalized_btm_mix["Battery / Other"]
        generation_share = solar_share + gas_share

        if generation_share > 0:
            solar_generation_weight = solar_share / generation_share
            gas_generation_weight = gas_share / generation_share
            results["estimated_cost_usd_per_mwh"] = (
                solar_generation_weight * solar_cost
                + gas_generation_weight * gas_cost
            )
        else:
            results["estimated_cost_usd_per_mwh"] = np.nan

        results["recommended_architecture"] = "Behind-the-Meter"
        results["power_mix_display"] = (
            f"Solar {solar_share:.0%} | "
            f"Gas {gas_share:.0%} | "
            f"Battery / Other {battery_share:.0%}"
        )

    results["annual_power_cost_usd"] = (
        results["estimated_cost_usd_per_mwh"] * annual_energy_mwh
    )
    results["grid_annual_cost_usd"] = grid_cost * annual_energy_mwh
    results["annual_savings_vs_grid_usd"] = (
        results["grid_annual_cost_usd"] - results["annual_power_cost_usd"]
    )

    return results


def add_reliability_scores(competitiveness_df, power_plan_df, power_strategy):
    if competitiveness_df is None:
        return None

    required = {"State", "capacity_score", "interconnection_score"}
    if not required.issubset(competitiveness_df.columns):
        return competitiveness_df.copy()

    reliability = competitiveness_df.copy()
    if (
        power_plan_df is not None
        and {"State", "recommended_architecture"}.issubset(power_plan_df.columns)
    ):
        architecture_lookup = power_plan_df[
            ["State", "recommended_architecture"]
        ].drop_duplicates()
        reliability = reliability.merge(
            architecture_lookup,
            on="State",
            how="left",
        )
    else:
        reliability["recommended_architecture"] = np.nan

    reliability["recommended_architecture"] = (
        reliability["recommended_architecture"].fillna(power_strategy)
    )

    reliability["architecture_diversification_score"] = (
        reliability["recommended_architecture"]
        .map(ARCHITECTURE_DIVERSIFICATION_SCORE)
        .fillna(0)
    )
    reliability["reliability_score"] = 100 * (
        0.40 * reliability["capacity_score"]
        + 0.35 * reliability["interconnection_score"]
        + 0.25 * reliability["architecture_diversification_score"]
    )

    return reliability


def build_community_summary(tradeoff_df, mitigation_df, scenario):
    if scenario is None:
        return None

    summary = {"scenario": scenario}

    if tradeoff_df is not None and "scenario" in tradeoff_df.columns:
        tradeoff_rows = tradeoff_df[tradeoff_df["scenario"] == scenario]
        if not tradeoff_rows.empty:
            tradeoff_row = tradeoff_rows.iloc[0]
            summary.update(
                {
                    "resident_cost_impact_usd_per_household": tradeoff_row.get(
                        "annual_cost_per_household_usd",
                        np.nan,
                    ),
                    "annual_community_cost_usd": tradeoff_row.get(
                        "annual_community_cost_usd",
                        np.nan,
                    ),
                    "annual_tax_revenue_usd": tradeoff_row.get(
                        "annual_tax_revenue_usd",
                        np.nan,
                    ),
                    "total_jobs_supported": tradeoff_row.get(
                        "total_jobs_supported",
                        np.nan,
                    ),
                }
            )

    if mitigation_df is not None and "scenario" in mitigation_df.columns:
        mitigation_rows = mitigation_df[mitigation_df["scenario"] == scenario]
        if not mitigation_rows.empty:
            mitigation_row = mitigation_rows.iloc[0]
            mitigation_percent = mitigation_row.get(
                "mitigation_as_percent_of_tax_revenue",
                np.nan,
            )
            summary.update(
                {
                    "mitigation_fund_requirement_usd": mitigation_row.get(
                        "required_mitigation_fund_usd",
                        np.nan,
                    ),
                    "mitigation_as_percent_of_tax_revenue": mitigation_percent,
                    "net_surplus_after_mitigation_usd": mitigation_row.get(
                        "net_fiscal_surplus_after_resident_offset_usd",
                        np.nan,
                    ),
                    "community_impact_score": (
                        np.clip(100 - mitigation_percent, 0, 100)
                        if pd.notna(mitigation_percent)
                        else np.nan
                    ),
                }
            )

    return summary


def describe_top_state(row, community_summary):
    upsides = []
    risks = []

    if pd.notna(row.get("custom_decision_score", np.nan)):
        upsides.append("Strong fit under the selected priority weighting.")

    if row.get("reliability_score", 0) >= 70:
        upsides.append("High reliability score from capacity and interconnection conditions.")
    else:
        risks.append("Reliability score may require additional power-risk diligence.")

    if row.get("interconnection_score", 0) >= 0.7:
        upsides.append("Lower relative interconnection friction in the current proxy.")
    else:
        risks.append("Interconnection conditions could slow power development.")

    if row.get("renewable_score", 0) >= 0.5:
        upsides.append("Renewable score supports lower-carbon sourcing options.")
    else:
        risks.append("Renewable availability may be more limited under current inputs.")

    if community_summary:
        mitigation_percent = community_summary.get(
            "mitigation_as_percent_of_tax_revenue",
            np.nan,
        )
        net_surplus = community_summary.get(
            "net_surplus_after_mitigation_usd",
            np.nan,
        )
        if pd.notna(net_surplus) and net_surplus > 0:
            upsides.append("Scenario-level community mitigation remains fiscally feasible.")
        if pd.notna(mitigation_percent) and mitigation_percent > 50:
            risks.append("Mitigation could consume a large share of local tax revenue.")

    if not risks:
        risks.append("Results are planning estimates and should be validated with project-specific engineering and local stakeholder analysis.")

    return upsides, risks


tables = load_tables()
eia_capacity, eia_capacity_status = load_optional_eia_capacity()
btm_inputs = load_btm_inputs()

# Notebook 3: regional competitiveness exports.
competitiveness = tables["competitiveness"]

# Notebook 5: behind-the-meter power architecture economics.
architecture = tables["architecture"]

# Notebook 4: Monte Carlo uncertainty and robustness outputs.
winner_frequency = tables["winner_frequency"]

# Community impact and mitigation notebooks.
community_tradeoff = tables["community_tradeoff"]
mitigation_fund = tables["mitigation_fund"]

# National power outlook notebook.
power_outlook = tables["power_outlook"]


st.title("AI Infrastructure Site Selection Dashboard")
st.caption(
    "Interactive decision support for evaluating state competitiveness, power "
    "architecture economics, reliability, and community impact."
)


with st.sidebar:
    st.header("Project Inputs")
    st.write("Dashboard tables are loaded from `outputs/tables/`.")
    st.caption(
        "Version 1 uses local CSV outputs and the stored AEO2026 dataset; "
        "no live EIA API calls or API keys are required."
    )
    if eia_capacity_status["source"] == "api":
        st.success("Live EIA data enabled")
    elif eia_capacity_status["source"] == "cache":
        st.warning("Using cached EIA capacity data")
    elif eia_capacity_status["source"] == "api_failed":
        st.warning("Live EIA refresh failed; using local CSV data")
    else:
        st.info("Using local CSV data")
    st.caption(eia_capacity_status["message"])

    load_status = []
    for key, filename in TABLES.items():
        path = TABLE_DIR / filename
        loaded = tables[key] is not None
        load_status.append(
            {
                "Table": filename,
                "Status": "Loaded" if loaded else "Missing",
                "Rows": len(tables[key]) if loaded else 0,
            }
        )

    st.dataframe(
        pd.DataFrame(load_status),
        hide_index=True,
        width="stretch",
    )

    desired_compute_load_mw = st.number_input(
        "Desired compute load (MW)",
        min_value=25,
        max_value=2_000,
        value=500,
        step=25,
        help="Planning input for the user scenario; source notebook outputs remain unchanged.",
    )

    region_preference = st.selectbox(
        "Region preference",
        options=[
            "No Preference",
            "West",
            "South",
            "Midwest",
            "Northeast",
        ],
    )

    power_sourcing_strategy = st.selectbox(
        "Power sourcing strategy",
        options=[
            "Grid Only",
            "Behind-the-Meter",
            "Hybrid",
        ],
    )

    if power_sourcing_strategy == "Behind-the-Meter":
        st.caption("Behind-the-meter power mix")
        solar_mix_pct = st.slider(
            "Solar %",
            min_value=0,
            max_value=100,
            value=50,
        )
        gas_mix_pct = st.slider(
            "Natural Gas %",
            min_value=0,
            max_value=100,
            value=40,
        )
        battery_other_mix_pct = st.slider(
            "Battery / Other %",
            min_value=0,
            max_value=100,
            value=10,
        )
    else:
        solar_mix_pct = 50
        gas_mix_pct = 40
        battery_other_mix_pct = 10

    normalized_btm_mix, raw_btm_mix_total = normalize_btm_mix(
        solar_mix_pct,
        gas_mix_pct,
        battery_other_mix_pct,
    )

    if (
        power_sourcing_strategy == "Behind-the-Meter"
        and raw_btm_mix_total != 100
    ):
        st.warning(
            "BTM power mix sliders should sum to 100%. "
            f"Current total is {raw_btm_mix_total:.0f}%, so the app will "
            "normalize the mix automatically for calculations."
        )

    st.divider()
    st.caption("Custom decision priorities")
    reliability_priority = st.slider(
        "Reliability priority",
        min_value=1,
        max_value=10,
        value=7,
    )
    renewable_priority = st.slider(
        "Renewable priority",
        min_value=1,
        max_value=10,
        value=6,
    )
    cost_priority = st.slider(
        "Cost priority",
        min_value=1,
        max_value=10,
        value=8,
    )
    interconnection_priority = st.slider(
        "Interconnection priority",
        min_value=1,
        max_value=10,
        value=7,
    )
    ecosystem_priority = float(
        np.mean(
            [
                reliability_priority,
                renewable_priority,
                cost_priority,
                interconnection_priority,
            ]
        )
    )

    user_priorities = {
        "Cost": float(cost_priority),
        "Reliability": float(reliability_priority),
        "Renewable": float(renewable_priority),
        "Ecosystem": ecosystem_priority,
        "Interconnection": float(interconnection_priority),
    }

    if competitiveness is not None and "State" in competitiveness.columns:
        state_options_df = add_region_column(competitiveness)
        if region_preference != "No Preference":
            state_options_df = state_options_df[
                state_options_df["Region"] == region_preference
            ]
        default_states = state_options_df["State"].dropna().tolist()
        selected_states = st.multiselect(
            "States",
            options=default_states,
            default=default_states,
            help="Filter ranking and economics views to selected states.",
        )
    else:
        selected_states = []

    if power_outlook is not None and "scenario" in power_outlook.columns:
        outlook_options = power_outlook["scenario"].dropna().tolist()
    else:
        outlook_options = []

    if outlook_options:
        outlook_scenario = st.selectbox(
            "Power outlook scenario",
            options=outlook_options,
            index=min(1, len(outlook_options) - 1),
        )
    else:
        outlook_scenario = None

    if community_tradeoff is not None and "scenario" in community_tradeoff.columns:
        community_options = community_tradeoff["scenario"].dropna().tolist()
    else:
        community_options = []

    if community_options:
        community_scenario = st.selectbox(
            "Community impact scenario",
            options=community_options,
            index=min(1, len(community_options) - 1),
        )
    else:
        community_scenario = None


competitiveness_view = apply_state_filters(
    competitiveness,
    selected_states,
    region_preference,
)
competitiveness_view, decision_weights = calculate_custom_decision_scores(
    competitiveness_view,
    user_priorities,
)

architecture_view = apply_state_filters(
    architecture,
    selected_states,
    region_preference,
)
power_plan_view = calculate_power_plan(
    architecture_view,
    power_sourcing_strategy,
    desired_compute_load_mw,
    normalized_btm_mix,
)
reliability_view = add_reliability_scores(
    competitiveness_view,
    power_plan_view,
    power_sourcing_strategy,
)
community_summary = build_community_summary(
    community_tradeoff,
    mitigation_fund,
    community_scenario,
)

recommendation_view = reliability_view.copy() if reliability_view is not None else None
if (
    recommendation_view is not None
    and power_plan_view is not None
    and "State" in recommendation_view.columns
    and "State" in power_plan_view.columns
):
    power_cols = [
        "State",
        "recommended_architecture",
        "estimated_cost_usd_per_mwh",
        "annual_power_cost_usd",
        "annual_savings_vs_grid_usd",
        "power_mix_display",
    ]
    available_power_cols = [
        col for col in power_cols
        if col in power_plan_view.columns
    ]
    recommendation_view = recommendation_view.merge(
        power_plan_view[available_power_cols],
        on="State",
        how="left",
        suffixes=("", "_power"),
    )

if recommendation_view is not None and "State" in recommendation_view.columns:
    recommendation_view = recommendation_view.copy()
    recommendation_view["state_abbr"] = recommendation_view["State"].map(STATE_ABBR)
    if "custom_decision_score" in recommendation_view.columns:
        recommendation_view = recommendation_view.sort_values(
            "custom_decision_score",
            ascending=False,
        )
        recommendation_view["rank"] = np.arange(1, len(recommendation_view) + 1)
    if community_summary:
        recommendation_view["community_mitigation_summary"] = (
            f"{community_summary.get('scenario', 'N/A')} scenario: "
            f"{format_number(community_summary.get('mitigation_fund_requirement_usd', np.nan), prefix='$')} fund; "
            f"{community_summary.get('mitigation_as_percent_of_tax_revenue', np.nan):.1f}% of tax revenue; "
            f"{format_number(community_summary.get('net_surplus_after_mitigation_usd', np.nan), prefix='$')} net surplus"
        )
    else:
        recommendation_view["community_mitigation_summary"] = (
            "Community scenario outputs unavailable"
        )


top_recommendation = None
if (
    recommendation_view is not None
    and "custom_decision_score" in recommendation_view.columns
    and not recommendation_view.empty
):
    top_recommendation = recommendation_view.sort_values(
        "custom_decision_score",
        ascending=False,
    ).iloc[0]

most_robust_state = None
winner_frequency_value = np.nan
if (
    winner_frequency is not None
    and {"State", "Winner_Frequency_Percent"}.issubset(winner_frequency.columns)
    and not winner_frequency.empty
):
    winner_kpi_view = apply_state_filters(
        winner_frequency,
        selected_states,
        region_preference,
    )
    if winner_kpi_view is not None and not winner_kpi_view.empty:
        winner_row = winner_kpi_view.sort_values(
            "Winner_Frequency_Percent",
            ascending=False,
        ).iloc[0]
        most_robust_state = winner_row["State"]
        winner_frequency_value = winner_row["Winner_Frequency_Percent"]

lowest_cost_architecture = None
lowest_cost_value = np.nan
if (
    architecture_view is not None
    and {"best_architecture", "lowest_cost_usd_per_mwh"}.issubset(
        architecture_view.columns
    )
    and not architecture_view.empty
):
    cost_row = architecture_view.sort_values("lowest_cost_usd_per_mwh").iloc[0]
    lowest_cost_architecture = (
        f"{cost_row['State']} - {cost_row['best_architecture']}"
    )
    lowest_cost_value = cost_row["lowest_cost_usd_per_mwh"]


kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
kpi_1.metric(
    "Recommended State",
    top_recommendation.get("State", "Unavailable")
    if top_recommendation is not None
    else "Unavailable",
)
kpi_2.metric(
    "Recommended Power Strategy",
    top_recommendation.get("recommended_architecture", power_sourcing_strategy)
    if top_recommendation is not None
    else power_sourcing_strategy,
)
kpi_3.metric(
    "Estimated Annual Power Cost",
    format_number(
        top_recommendation.get("annual_power_cost_usd", np.nan),
        prefix="$",
    )
    if top_recommendation is not None
    else "N/A",
)
kpi_4.metric(
    "Reliability Score",
    f"{top_recommendation.get('reliability_score', np.nan):.1f}"
    if (
        top_recommendation is not None
        and pd.notna(top_recommendation.get("reliability_score", np.nan))
    )
    else "N/A",
)

st.divider()

if (
    recommendation_view is not None
    and {"state_abbr", "custom_decision_score", "State"}.issubset(
        recommendation_view.columns
    )
    and not recommendation_view.empty
):
    st.subheader("Candidate State Map")
    st.caption(
        "States are colored by the current custom decision score. Tooltips "
        "show power cost, reliability, and recommended architecture."
    )
    map_data = recommendation_view.dropna(
        subset=["state_abbr", "custom_decision_score"]
    ).copy()
    for tooltip_col in [
        "annual_power_cost_usd",
        "reliability_score",
        "recommended_architecture",
    ]:
        if tooltip_col not in map_data.columns:
            map_data[tooltip_col] = (
                "Unavailable"
                if tooltip_col == "recommended_architecture"
                else np.nan
            )
    fig = px.choropleth(
        map_data,
        locations="state_abbr",
        locationmode="USA-states",
        color="custom_decision_score",
        scope="usa",
        color_continuous_scale="Blues",
        hover_name="State",
        hover_data={
            "state_abbr": False,
            "custom_decision_score": ":.3f",
            "annual_power_cost_usd": ":,.0f",
            "reliability_score": ":.1f",
            "recommended_architecture": True,
        },
        labels={
            "custom_decision_score": "Decision Score",
            "annual_power_cost_usd": "Annual Power Cost ($)",
            "reliability_score": "Reliability Score",
            "recommended_architecture": "Architecture",
        },
        title="AI Infrastructure Site Selection Map",
    )
    fig.update_layout(
        template="plotly_white",
        height=520,
        margin=dict(l=10, r=10, t=60, b=10),
        geo=dict(bgcolor="rgba(0,0,0,0)", lakecolor="white"),
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader("Top State Ranking")
    ranking_cols = [
        "rank",
        "State",
        "custom_decision_score",
        "recommended_architecture",
        "annual_power_cost_usd",
        "reliability_score",
        "community_mitigation_summary",
    ]
    available_ranking_cols = [
        col for col in ranking_cols
        if col in recommendation_view.columns
    ]
    st.dataframe(
        recommendation_view[available_ranking_cols].sort_values("rank"),
        hide_index=True,
        width="stretch",
    )

st.subheader("Power Architecture Cost Comparison")
if architecture_view is not None and not architecture_view.empty:
    architecture_cost_cols = [
        "grid_cost_usd_per_mwh",
        "gas_cost_usd_per_mwh",
        "solar_cost_usd_per_mwh",
        "hybrid_cost_usd_per_mwh",
    ]
    if {"State", *architecture_cost_cols}.issubset(architecture_view.columns):
        architecture_long = architecture_view.melt(
            id_vars="State",
            value_vars=architecture_cost_cols,
            var_name="Architecture",
            value_name="Cost ($/MWh)",
        )
        architecture_long["Architecture"] = (
            architecture_long["Architecture"]
            .str.replace("_cost_usd_per_mwh", "", regex=False)
            .str.title()
        )
        fig = px.bar(
            architecture_long,
            x="State",
            y="Cost ($/MWh)",
            color="Architecture",
            barmode="group",
            color_discrete_sequence=px.colors.qualitative.Set2,
            title="Grid, Gas, Solar, and Hybrid Cost by State",
        )
        fig.update_layout(
            template="plotly_white",
            height=470,
            margin=dict(l=20, r=20, t=60, b=20),
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info(
            "Architecture cost columns are unavailable in the selected output table."
        )
else:
    st.info("Power architecture outputs are unavailable for the selected states.")

st.subheader("Community Benefits vs Mitigation Costs")
st.caption(
    "Community results are scenario-based and not location-specific unless "
    "state-level community data is added later."
)
if community_tradeoff is not None:
    community_chart = community_tradeoff.copy()
    if mitigation_fund is not None and "scenario" in mitigation_fund.columns:
        mitigation_cols = [
            col for col in [
                "scenario",
                "required_mitigation_fund_usd",
                "mitigation_as_percent_of_tax_revenue",
            ]
            if col in mitigation_fund.columns
        ]
        community_chart = community_chart.merge(
            mitigation_fund[mitigation_cols],
            on="scenario",
            how="left",
        )
    community_value_cols = [
        col for col in [
            "annual_tax_revenue_usd",
            "annual_community_cost_usd",
            "required_mitigation_fund_usd",
            "net_fiscal_surplus_after_resident_offset_usd",
        ]
        if col in community_chart.columns
    ]
    if community_value_cols:
        community_long = community_chart.melt(
            id_vars="scenario",
            value_vars=community_value_cols,
            var_name="Metric",
            value_name="USD",
        )
        community_long["Metric"] = (
            community_long["Metric"]
            .str.replace("_", " ", regex=False)
            .str.title()
        )
        fig = px.bar(
            community_long,
            x="scenario",
            y="USD",
            color="Metric",
            barmode="group",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            title="Community Benefits, Costs, and Mitigation Requirements",
        )
        fig.update_layout(
            template="plotly_white",
            height=470,
            margin=dict(l=20, r=20, t=60, b=20),
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Community benefit and mitigation columns are unavailable.")
else:
    st.info("Community impact outputs are unavailable.")


tabs = st.tabs(
    [
        "State Competitiveness",
        "Power Architecture",
        "Reliability & Uncertainty",
        "National Power Outlook",
        "Community Impact",
        "Data Tables",
    ]
)


with tabs[0]:
    # Connects to Notebook 3: final regional competitiveness scoring.
    section_header(
        "State Competitiveness",
        "Notebook 3 output plus user-weighted decision scoring across price, "
        "capacity, renewable, ecosystem, and interconnection factors.",
    )
    if require_table(competitiveness_view, TABLES["competitiveness"]):
        if decision_weights:
            weight_display = pd.DataFrame(
                [
                    {
                        "Score Factor": col,
                        "Normalized Weight": weight,
                    }
                    for col, weight in decision_weights.items()
                ]
            )
            st.dataframe(
                weight_display,
                hide_index=True,
                width="stretch",
            )

        required = {"State", "custom_decision_score"}
        if required.issubset(competitiveness_view.columns):
            chart_data = competitiveness_view.sort_values(
                "custom_decision_score",
                ascending=True,
            )
            fig = px.bar(
                chart_data,
                x="custom_decision_score",
                y="State",
                orientation="h",
                title="Custom AI Infrastructure Site Selection Score",
                labels={
                    "custom_decision_score": "Custom Decision Score",
                    "State": "",
                },
            )
            fig.update_layout(height=520, margin=dict(l=20, r=20, t=60, b=20))
            st.plotly_chart(fig, width="stretch")

        score_cols = [
            "State",
            "Region",
            "custom_decision_score",
            "competitiveness_score",
            "price_score",
            "capacity_score",
            "renewable_score",
            "ecosystem_score",
            "interconnection_score",
        ]
        available_cols = [
            col for col in score_cols
            if col in competitiveness_view.columns
        ]
        st.dataframe(
            competitiveness_view[available_cols].sort_values(
                "custom_decision_score",
                ascending=False,
            ),
            hide_index=True,
            width="stretch",
        )

        if (
            recommendation_view is not None
            and "custom_decision_score" in recommendation_view.columns
            and not recommendation_view.empty
        ):
            st.divider()
            st.subheader("Top Recommended States")
            st.caption(
                "Top recommendations combine the user-weighted site-selection "
                "score with reliability and power-cost estimates. Community "
                "impact is scenario-based and not location-specific unless "
                "state-level community data is added later."
            )

            top_recommendations = (
                recommendation_view
                .sort_values("custom_decision_score", ascending=False)
                .head(3)
            )
            summary_cols = [
                "State",
                "Region",
                "custom_decision_score",
                "reliability_score",
                "recommended_architecture",
                "estimated_cost_usd_per_mwh",
                "annual_power_cost_usd",
                "annual_savings_vs_grid_usd",
                "power_mix_display",
            ]
            available_summary_cols = [
                col for col in summary_cols
                if col in top_recommendations.columns
            ]
            st.dataframe(
                top_recommendations[available_summary_cols],
                hide_index=True,
                width="stretch",
            )

            for _, row in top_recommendations.iterrows():
                upsides, risks = describe_top_state(row, community_summary)
                with st.expander(f"{row['State']} decision notes", expanded=False):
                    c1, c2, c3 = st.columns(3)
                    c1.metric(
                        "Reliability Score",
                        f"{row.get('reliability_score', np.nan):.1f}"
                        if pd.notna(row.get("reliability_score", np.nan))
                        else "N/A",
                    )
                    c2.metric(
                        "Estimated Cost",
                        f"${row.get('estimated_cost_usd_per_mwh', np.nan):.1f}/MWh"
                        if pd.notna(row.get("estimated_cost_usd_per_mwh", np.nan))
                        else "N/A",
                    )
                    c3.metric(
                        "Annual Savings vs Grid",
                        format_number(
                            row.get("annual_savings_vs_grid_usd", np.nan),
                            prefix="$",
                        ),
                    )
                    st.write("Community Impact / Mitigation Summary")
                    if community_summary:
                        st.write(
                            f"Scenario: {community_summary.get('scenario', 'N/A')} | "
                            "Resident cost impact: "
                            f"{format_number(community_summary.get('resident_cost_impact_usd_per_household', np.nan), prefix='$', suffix='/hh')} | "
                            "Mitigation fund: "
                            f"{format_number(community_summary.get('mitigation_fund_requirement_usd', np.nan), prefix='$')} | "
                            "Mitigation share of tax revenue: "
                            f"{community_summary.get('mitigation_as_percent_of_tax_revenue', np.nan):.1f}% | "
                            "Net surplus after mitigation: "
                            f"{format_number(community_summary.get('net_surplus_after_mitigation_usd', np.nan), prefix='$')}"
                        )
                    else:
                        st.write(
                            "Community scenario outputs are unavailable for this run."
                        )
                    st.write("Key Upsides")
                    for item in upsides:
                        st.write(f"- {item}")
                    st.write("Key Risks")
                    for item in risks:
                        st.write(f"- {item}")


with tabs[1]:
    # Connects to Notebook 5: grid, gas, solar, and hybrid architecture costs.
    section_header(
        "Power Architecture Economics",
        "Notebook 5 output: compares grid, gas, solar, and hybrid power costs "
        "for behind-the-meter AI infrastructure scenarios.",
    )
    if btm_inputs is not None and "solar_capacity_factor" in btm_inputs.columns:
        st.caption(
            "Solar capacity factors are local NREL PVWatts-derived inputs from "
            "`sources/btm_inputs.csv`."
        )
    if require_table(architecture_view, TABLES["architecture"]):
        cost_cols = [
            "grid_cost_usd_per_mwh",
            "gas_cost_usd_per_mwh",
            "solar_cost_usd_per_mwh",
            "hybrid_cost_usd_per_mwh",
        ]
        st.info(
            "BTM and hybrid calculations are simplified planning estimates "
            "based on exported Notebook 5 cost fields. They are not "
            "dispatch-optimized engineering results."
        )

        if power_sourcing_strategy == "Behind-the-Meter":
            st.caption(
                "Battery / Other is treated as a reliability allocation because "
                "separate battery dispatch cost data is not implemented in the "
                "repo outputs. The blended BTM $/MWh is calculated from the "
                "solar and gas generation portions."
            )
            mix_cols = st.columns(3)
            mix_cols[0].metric("Normalized Solar Mix", f"{normalized_btm_mix['Solar']:.0%}")
            mix_cols[1].metric(
                "Normalized Gas Mix",
                f"{normalized_btm_mix['Natural Gas']:.0%}",
            )
            mix_cols[2].metric(
                "Reliability Allocation",
                f"{normalized_btm_mix['Battery / Other']:.0%}",
            )

        if power_plan_view is not None and not power_plan_view.empty:
            best_power_row = power_plan_view.sort_values(
                "annual_power_cost_usd",
                ascending=True,
            ).iloc[0]
            c1, c2, c3 = st.columns(3)
            c1.metric("Selected Strategy", power_sourcing_strategy)
            c2.metric(
                "Lowest Estimated Cost",
                f"${best_power_row['estimated_cost_usd_per_mwh']:.1f}/MWh",
                best_power_row["State"],
            )
            c3.metric(
                "Annual Savings vs Grid",
                format_number(
                    best_power_row["annual_savings_vs_grid_usd"],
                    prefix="$",
                ),
            )

            fig = px.bar(
                power_plan_view.sort_values(
                    "annual_power_cost_usd",
                    ascending=True,
                ),
                x="State",
                y="annual_power_cost_usd",
                title=(
                    "Estimated Annual Power Cost "
                    f"({desired_compute_load_mw:,.0f} MW)"
                ),
                labels={
                    "annual_power_cost_usd": "Annual Power Cost ($)",
                    "State": "State",
                },
            )
            fig.update_layout(height=440, margin=dict(l=20, r=20, t=60, b=20))
            st.plotly_chart(fig, width="stretch")

            plan_cols = [
                "State",
                "recommended_architecture",
                "estimated_cost_usd_per_mwh",
                "annual_power_cost_usd",
                "annual_savings_vs_grid_usd",
                "power_mix_display",
            ]
            st.dataframe(
                power_plan_view[plan_cols].sort_values(
                    "annual_power_cost_usd",
                    ascending=True,
                ),
                hide_index=True,
                width="stretch",
            )

        if {"State", *cost_cols}.issubset(architecture_view.columns):
            long_costs = architecture_view.melt(
                id_vars="State",
                value_vars=cost_cols,
                var_name="Architecture",
                value_name="Cost ($/MWh)",
            )
            long_costs["Architecture"] = (
                long_costs["Architecture"]
                .str.replace("_cost_usd_per_mwh", "", regex=False)
                .str.title()
            )
            fig = px.bar(
                long_costs,
                x="State",
                y="Cost ($/MWh)",
                color="Architecture",
                barmode="group",
                title="Power Cost Architecture Comparison",
            )
            fig.update_layout(height=520, margin=dict(l=20, r=20, t=60, b=20))
            st.plotly_chart(fig, width="stretch")

        if (
            btm_inputs is not None
            and {"State", "solar_capacity_factor"}.issubset(btm_inputs.columns)
        ):
            solar_view = apply_state_filters(
                btm_inputs,
                selected_states,
                region_preference,
            )
            if solar_view is not None and not solar_view.empty:
                st.subheader("NREL PVWatts Solar Capacity Factors")
                fig = px.bar(
                    solar_view.sort_values("solar_capacity_factor"),
                    x="solar_capacity_factor",
                    y="State",
                    orientation="h",
                    title="Utility-Scale Solar Capacity Factor Inputs",
                    labels={
                        "solar_capacity_factor": "Solar Capacity Factor (%)",
                        "State": "",
                    },
                )
                fig.update_layout(
                    height=360,
                    margin=dict(l=20, r=20, t=60, b=20),
                )
                st.plotly_chart(fig, width="stretch")

        display_cols = [
            "State",
            "best_architecture",
            "lowest_cost_usd_per_mwh",
            "grid_cost_usd_per_mwh",
            "gas_cost_usd_per_mwh",
            "solar_cost_usd_per_mwh",
            "hybrid_cost_usd_per_mwh",
        ]
        available_cols = [
            col for col in display_cols
            if col in architecture_view.columns
        ]
        st.dataframe(
            architecture_view[available_cols].sort_values(
                "lowest_cost_usd_per_mwh",
                ascending=True,
            ),
            hide_index=True,
            width="stretch",
        )


with tabs[2]:
    # Connects to Notebook 4: randomized weight scenarios for model robustness.
    section_header(
        "Reliability & Uncertainty",
        "Notebook 4 output: Monte Carlo winner frequency plus operational "
        "readiness proxies from the competitiveness model.",
    )
    col_left, col_right = st.columns([1.1, 1])

    with col_left:
        if require_table(winner_frequency, TABLES["winner_frequency"]):
            if {"State", "Winner_Frequency_Percent"}.issubset(
                winner_frequency.columns
            ):
                winner_view = apply_state_filters(
                    winner_frequency,
                    selected_states,
                    region_preference,
                )
                winner_view = winner_view.sort_values(
                    "Winner_Frequency_Percent",
                    ascending=True,
                )
                fig = px.bar(
                    winner_view,
                    x="Winner_Frequency_Percent",
                    y="State",
                    orientation="h",
                    title="Monte Carlo Winner Frequency",
                    labels={
                        "Winner_Frequency_Percent": "Winner Frequency (%)",
                        "State": "",
                    },
                )
                fig.update_layout(height=480, margin=dict(l=20, r=20, t=60, b=20))
                st.plotly_chart(fig, width="stretch")

    with col_right:
        if require_table(reliability_view, TABLES["competitiveness"]):
            reliability_cols = [
                "State",
                "reliability_score",
                "capacity_score",
                "interconnection_score",
                "architecture_diversification_score",
                "recommended_architecture",
                "Interconnection_Region",
            ]
            available_cols = [
                col for col in reliability_cols
                if col in reliability_view.columns
            ]
            st.write("Reliability score components")
            if "reliability_score" in reliability_view.columns:
                fig = px.bar(
                    reliability_view.sort_values(
                        "reliability_score",
                        ascending=True,
                    ),
                    x="reliability_score",
                    y="State",
                    orientation="h",
                    title="Reliability Score by State",
                    labels={
                        "reliability_score": "Reliability Score (0-100)",
                        "State": "",
                    },
                )
                fig.update_layout(height=360, margin=dict(l=20, r=20, t=60, b=20))
                st.plotly_chart(fig, width="stretch")

            st.dataframe(
                reliability_view[available_cols].sort_values(
                    "reliability_score",
                    ascending=False,
                ),
                hide_index=True,
                width="stretch",
            )


with tabs[3]:
    # Connects to the national power outlook notebook and 2030 scenario table.
    section_header(
        "National Power Outlook Through 2030",
        "National outlook output: demand growth and capacity realization "
        "scenarios for electricity planning context.",
    )
    st.caption(
        "This section loads `outputs/tables/national_power_outlook_2030.csv`, "
        "which is generated from the stored `data/raw/AEO2026.zip` source file."
    )
    if require_table(power_outlook, TABLES["power_outlook"]):
        if {
            "scenario",
            "projected_2030_demand_mwh",
            "projected_2030_capacity_mw",
        }.issubset(power_outlook.columns):
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=power_outlook["scenario"],
                    y=power_outlook["projected_2030_demand_mwh"],
                    name="Projected 2030 Demand (MWh)",
                    yaxis="y",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=power_outlook["scenario"],
                    y=power_outlook["projected_2030_capacity_mw"],
                    name="Projected 2030 Capacity (MW)",
                    yaxis="y2",
                    mode="lines+markers",
                )
            )
            fig.update_layout(
                title="National Demand and Capacity Outlook",
                yaxis=dict(title="Demand (MWh)"),
                yaxis2=dict(
                    title="Capacity (MW)",
                    overlaying="y",
                    side="right",
                ),
                height=500,
                margin=dict(l=20, r=20, t=60, b=20),
            )
            st.plotly_chart(fig, width="stretch")

        if outlook_scenario is not None:
            scenario_rows = power_outlook[
                power_outlook["scenario"] == outlook_scenario
            ]
            if not scenario_rows.empty:
                row = scenario_rows.iloc[0]
                c1, c2, c3 = st.columns(3)
                c1.metric(
                    "Demand Growth",
                    f"{row.get('demand_growth_percent', np.nan):.0f}%",
                )
                c2.metric(
                    "Capacity Realization",
                    f"{row.get('capacity_realization_percent', np.nan):.0f}%",
                )
                c3.metric(
                    "Capacity Growth",
                    format_number(row.get("capacity_growth_mw", np.nan), suffix=" MW"),
                )

        st.dataframe(power_outlook, hide_index=True, width="stretch")

        if eia_capacity is not None and not eia_capacity.empty:
            st.divider()
            st.subheader("Optional Live EIA Capacity Extract")
            st.caption(
                "State-level generating capacity by energy source is loaded "
                "from the live EIA API when `EIA_API_KEY` is set, otherwise "
                "from the local cache if available."
            )
            latest_period = eia_capacity["period"].max()
            latest_capacity = eia_capacity[
                eia_capacity["period"] == latest_period
            ].copy()
            if {
                "state",
                "energy_source_description",
                "generating_capacity_mw",
            }.issubset(latest_capacity.columns):
                capacity_by_source = (
                    latest_capacity
                    .groupby("energy_source_description", as_index=False)[
                        "generating_capacity_mw"
                    ]
                    .sum()
                    .sort_values("generating_capacity_mw", ascending=False)
                    .head(12)
                )
                fig = px.bar(
                    capacity_by_source,
                    x="energy_source_description",
                    y="generating_capacity_mw",
                    title=(
                        "Latest EIA Generating Capacity by Energy Source "
                        f"({latest_period})"
                    ),
                    labels={
                        "energy_source_description": "Energy Source",
                        "generating_capacity_mw": "Generating Capacity (MW)",
                    },
                )
                fig.update_layout(
                    height=420,
                    margin=dict(l=20, r=20, t=60, b=80),
                    xaxis_tickangle=-35,
                )
                st.plotly_chart(fig, width="stretch")


with tabs[4]:
    # Connects to the community impact and mitigation output tables.
    section_header(
        "Community Impact and Mitigation",
        "Community impact outputs: local benefits, household cost exposure, "
        "and mitigation fund sizing.",
    )
    st.info(
        "Community scoring is scenario-based and not location-specific. "
        "State-level community scoring can be added later if local burden, "
        "ratepayer, and mitigation data are collected by state or project site."
    )

    if community_summary:
        st.subheader("Community Impact / Mitigation Summary")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Resident Cost Impact",
            format_number(
                community_summary.get(
                    "resident_cost_impact_usd_per_household",
                    np.nan,
                ),
                prefix="$",
                suffix="/hh",
            ),
        )
        c2.metric(
            "Mitigation Fund Requirement",
            format_number(
                community_summary.get("mitigation_fund_requirement_usd", np.nan),
                prefix="$",
            ),
        )
        c3.metric(
            "Mitigation % of Tax Revenue",
            f"{community_summary.get('mitigation_as_percent_of_tax_revenue', np.nan):.1f}%"
            if pd.notna(
                community_summary.get(
                    "mitigation_as_percent_of_tax_revenue",
                    np.nan,
                )
            )
            else "N/A",
        )
        c4.metric(
            "Community Impact Score",
            f"{community_summary.get('community_impact_score', np.nan):.1f}"
            if pd.notna(community_summary.get("community_impact_score", np.nan))
            else "N/A",
        )
        st.metric(
            "Net Surplus After Mitigation",
            format_number(
                community_summary.get("net_surplus_after_mitigation_usd", np.nan),
                prefix="$",
            ),
        )

    if require_table(community_tradeoff, TABLES["community_tradeoff"]):
        if {
            "scenario",
            "annual_tax_revenue_usd",
            "annual_community_cost_usd",
            "net_fiscal_surplus_after_resident_offset_usd",
        }.issubset(community_tradeoff.columns):
            tradeoff_long = community_tradeoff.melt(
                id_vars="scenario",
                value_vars=[
                    "annual_tax_revenue_usd",
                    "annual_community_cost_usd",
                    "net_fiscal_surplus_after_resident_offset_usd",
                ],
                var_name="Metric",
                value_name="USD",
            )
            tradeoff_long["Metric"] = (
                tradeoff_long["Metric"]
                .str.replace("_", " ", regex=False)
                .str.title()
            )
            fig = px.bar(
                tradeoff_long,
                x="scenario",
                y="USD",
                color="Metric",
                barmode="group",
                title="Community Fiscal Tradeoff by Scenario",
            )
            fig.update_layout(height=500, margin=dict(l=20, r=20, t=60, b=20))
            st.plotly_chart(fig, width="stretch")

        if community_scenario is not None:
            row = community_tradeoff[
                community_tradeoff["scenario"] == community_scenario
            ]
            if not row.empty:
                row = row.iloc[0]
                c1, c2, c3 = st.columns(3)
                c1.metric(
                    "Jobs Supported",
                    format_number(row.get("total_jobs_supported", np.nan)),
                )
                c2.metric(
                    "Annual Tax Revenue",
                    format_number(
                        row.get("annual_tax_revenue_usd", np.nan),
                        prefix="$",
                    ),
                )
                c3.metric(
                    "Resident Cost Offset",
                    format_number(
                        row.get("annual_community_cost_usd", np.nan),
                        prefix="$",
                    ),
                )

        st.dataframe(
            community_tradeoff,
            hide_index=True,
            width="stretch",
        )

    if mitigation_fund is not None:
        st.divider()
        st.write("Mitigation fund sizing")
        st.dataframe(mitigation_fund, hide_index=True, width="stretch")


with tabs[5]:
    section_header(
        "Data Tables",
        "Raw dashboard inputs loaded from exported notebook outputs.",
    )
    for key, filename in TABLES.items():
        with st.expander(filename, expanded=False):
            df = tables[key]
            if df is None:
                st.warning(f"`outputs/tables/{filename}` is missing.")
            else:
                st.dataframe(df, hide_index=True, width="stretch")

    with st.expander("eia_generating_capacity_by_state_source.csv", expanded=False):
        st.caption(eia_capacity_status["message"])
        if eia_capacity is None:
            st.warning(
                "`outputs/tables/eia_generating_capacity_by_state_source.csv` "
                "is not available yet. Set `EIA_API_KEY` to enable the optional "
                "live EIA refresh."
            )
        else:
            st.dataframe(eia_capacity, hide_index=True, width="stretch")

    with st.expander("sources/btm_inputs.csv", expanded=False):
        st.caption(
            "Includes NREL PVWatts-derived solar capacity factor inputs used "
            "by the behind-the-meter economics notebook."
        )
        if btm_inputs is None:
            st.warning("`sources/btm_inputs.csv` is missing.")
        else:
            st.dataframe(btm_inputs, hide_index=True, width="stretch")
