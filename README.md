# Final Results and Executive Summary

## Executive Summary

This project developed a quantitative framework for evaluating AI infrastructure competitiveness across the United States. The analysis combines regional competitiveness modeling, Monte Carlo simulation, behind-the-meter power economics, national power outlook scenarios, and community impact analysis.

The objective was not to predict the exact location of future AI infrastructure deployment but to identify the factors most likely to influence where AI infrastructure can be built, how it can be powered, and how communities may be affected by its expansion.

---

# Key Finding 1: Power Economics Are Becoming a Primary Constraint

Historically, data center deployment decisions were influenced by land availability, tax incentives, and network connectivity.

The results of this framework suggest that electricity availability and power economics are becoming increasingly important determinants of AI infrastructure competitiveness.

As AI workloads grow, access to reliable, scalable, and affordable electricity may become one of the primary constraints on future infrastructure expansion.

---

# Key Finding 2: Texas Emerges as the Strongest Overall State

Across the regional competitiveness framework and Monte Carlo simulations, Texas consistently emerged as the strongest overall deployment location.

Several factors contributed to this result:

- Low electricity prices
- Large generation capacity
- Existing infrastructure ecosystem
- Favorable interconnection conditions
- Strong behind-the-meter potential

Texas also demonstrated the highest robustness across randomized weighting scenarios.

---

# Key Finding 3: Interconnection Constraints Matter

The addition of an interconnection friction score significantly improved the realism of the framework.

Infrastructure competitiveness is not determined solely by power availability. The ability to access transmission infrastructure and navigate interconnection queues may become increasingly important as AI electricity demand grows.

The results suggest that transmission bottlenecks may influence deployment decisions nearly as much as electricity prices.

---

# Key Finding 4: Optimal Power Architecture Depends on Geography

No single power architecture dominates every region.

The behind-the-meter economics framework suggests that:

- Natural gas generation remains attractive in states with low fuel costs.
- Solar generation becomes increasingly attractive in regions with strong solar resources.
- Hybrid systems combining solar, storage, and backup generation may provide the most balanced long-term solution. This is important as it is the most reliable system, something the model struggles to factor in and would be added in stage 2.

This suggests that future AI infrastructure deployment strategies may become increasingly location-specific.

---

# Key Finding 5: National Power Demand Is Growing Faster Than Many Existing Planning Assumptions

The national power outlook framework suggests that AI-driven electricity demand growth could place increasing pressure on the U.S. power system by 2030.

Although substantial generation additions are planned, future outcomes depend heavily on project completion rates and demand growth assumptions.

The results reinforce the importance of generation expansion, transmission investment, and alternative power strategies.

---

# Key Finding 6: Community Opposition May Be a Distribution Problem

The community impact framework produced one of the most interesting findings of the project.

Large AI infrastructure projects may create meaningful local costs through:

- Electricity price increases
- Construction disruption
- Traffic
- Noise
- Land use impacts

However, these projects also generate substantial tax revenue and economic activity.

Under baseline assumptions, modeled local tax revenues exceeded the estimated cost of offsetting residential electricity bill impacts. This suggests that targeted mitigation programs may allow communities to share more directly in the economic benefits of infrastructure development.

The difference between electricity prices and tax revenue could subsidize costs for residents while mitigating negative externalities.

---

# Limitations

Several limitations remain.

The framework uses simplified assumptions and proxies for a number of variables, including:

- Interconnection friction
- Community burden estimates
- Behind-the-meter deployment potential
- Reliability in power sourcing

The analysis should therefore be interpreted as a comparative decision-support framework rather than a predictive forecasting model.

Future versions may incorporate:

- State-level queue duration data
- Dispatch optimization
- Reliability metrics
- Water constraints
- Nuclear and geothermal scenarios
- Capacity expansion modeling
- Source location diversification

---

# Conclusion

The results suggest that future AI infrastructure deployment will be shaped increasingly by power economics, grid constraints, and energy availability.

While Texas currently appears to possess the strongest overall combination of infrastructure advantages, the optimal deployment strategy varies substantially across regions and power market conditions.

The broader implication is that AI infrastructure development is no longer solely a computing problem. It is increasingly an energy, infrastructure, and community planning problem.

Organizations that can successfully align power strategy, infrastructure economics, and community outcomes may be best positioned to support the next generation of AI growth.

# Repository Structure

The project is organized into nine notebooks that progressively build the research framework.

| Notebook | Purpose |
|-----------|----------|
| 01_data_collection | Data sources, documentation, and variable construction |
| 02_baseline_model | Model development notes, assumptions, and framework design |
| 03_regional_competitiveness | State-level AI infrastructure competitiveness model |
| 04_monte_carlo | Robustness testing using 10,000 Monte Carlo simulations |
| 05_behind_the_meter | Grid, natural gas, solar, and hybrid power economics |
| 06_visualizations | Final publication-quality figures and charts |
| 07_national_power_outlook_2030 | National electricity demand and capacity outlook scenarios |
| 08_community_impact_and_mitigation | Local economic impacts, electricity costs, and mitigation analysis |
| 09_final_results | Executive summary, findings, conclusions, and future research |

---

## Interactive Decision-Support Dashboard

This repository includes a Streamlit dashboard that turns the research outputs into an interactive AI infrastructure site-selection tool.

The dashboard evaluates state competitiveness, power architecture economics, reliability, uncertainty, national power outlook scenarios, and community impact tradeoffs using the CSV outputs generated by the project notebooks.

Users can adjust:

- Desired compute load in MW
- Region preference
- Power sourcing strategy
- Reliability, renewable, cost, and interconnection priorities
- Behind-the-meter solar, natural gas, and battery / other mix assumptions
- Community impact and national power outlook scenarios

The dashboard provides:

- Recommended state and power strategy
- Estimated annual power cost
- Reliability score
- Interactive state map colored by custom decision score
- State ranking table
- Grid, gas, solar, and hybrid architecture cost comparisons
- Community benefits and mitigation cost summaries

To run locally:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The dashboard uses simplified planning assumptions and is intended as a decision-support prototype, not an engineering-grade siting tool.

---

## Static AEO2026 Power Outlook Data

Version 1 uses `data/raw/AEO2026.zip` as a stored U.S. Energy Information Administration Annual Energy Outlook source dataset. The Streamlit dashboard does not require live EIA API calls or API keys.

The processing script extracts national power outlook series from the stored AEO2026 file and writes:

- `data/processed/aeo2026_power_outlook.csv`
- `outputs/tables/national_power_outlook_2030.csv`

To regenerate the local power outlook table:

```bash
python scripts/process_aeo2026_power_outlook.py
```

The current processor maps AEO2026 scenarios into the dashboard's Low, Baseline, and High national outlook cases using total electricity use and cumulative planned electric-power-sector additions. Future versions may optionally support live EIA API updates, but the Version 1 dashboard is designed to run fully from local CSV files.

---

## Optional EIA API Refresh

The dashboard can optionally refresh state-level generating capacity by energy source from the EIA v2 API. This is an enhancement only: the dashboard still runs from local CSV files when no API key is available.

Set the API key as an environment variable:

```bash
export EIA_API_KEY="your_key_here"
streamlit run streamlit_app.py
```

Do not hard-code the key in the repository. Local `.env` files are ignored by git.

When enabled, the app calls:

```text
https://api.eia.gov/v2/electricity/state-electricity-profiles/capability/data/
```

Successful API results are cached to:

```text
outputs/tables/eia_generating_capacity_by_state_source.csv
```

If the API call fails, the dashboard falls back to that cached CSV when available. If neither live API data nor cache data is available, the dashboard continues using the core local notebook output CSVs.

---

# Methodology Overview

The project combines five complementary analytical frameworks.

### 1. Regional Competitiveness Framework

Evaluates state-level attractiveness for AI infrastructure deployment using:

- Electricity Price
- Grid Capacity
- Renewable Energy Share
- Existing Data Center Ecosystem
- Behind-the-Meter Potential
- Interconnection Friction

### 2. Monte Carlo Robustness Analysis

10,000 simulations were performed using randomized weighting assumptions generated through a Dirichlet distribution.

Outputs include:

- Winner Frequency
- Top-Three Frequency
- Median Competitiveness
- Competitiveness Volatility

### 3. Behind-the-Meter Infrastructure Economics

Compares:

- Grid Power
- Natural Gas Generation
- Solar Generation
- Hybrid Solar + Storage + Gas Systems

to determine the lowest-cost power architecture under different regional conditions.

### 4. National Power Outlook Through 2030

Evaluates whether planned U.S. generation additions appear sufficient to support projected AI-driven electricity demand growth under low, baseline, and high growth scenarios.

### 5. Community Impact and Mitigation Economics

Evaluates:

- Job Creation
- Local Tax Revenue
- Resident Electricity Cost Impacts
- Community Mitigation Strategies

to estimate whether AI infrastructure projects can offset local burdens while maintaining positive economic benefits.

---

# Key Visualizations

The most important outputs include:

- State Competitiveness Rankings
- Monte Carlo Winner Frequency
- Strength vs Robustness Analysis
- Power Architecture Comparison
- Break-Even Power Cost Curves
- National Power Outlook Scenarios
- Community Benefits vs Mitigation Costs

Figures are located in:

text outputs/figures/ 

---

# Data Sources

Primary data sources include:

- U.S. Energy Information Administration (EIA)
- Lawrence Berkeley National Laboratory (LBNL)
- International Energy Agency (IEA)
- Electric Power Research Institute (EPRI)
- National Renewable Energy Laboratory (NREL)
- U.S. Energy Information Administration Annual Energy Outlook 2026 stored dataset
- DataCenterMap
- PJM
- MISO
- CAISO
- ERCOT

Additional details and citations are provided within the notebooks and paper materials.

---

# Future Research

Potential future extensions include:

- State-level interconnection queue duration modeling
- Dispatch optimization for hybrid power systems
- Nuclear and geothermal deployment scenarios
- Capacity expansion modeling
- Reliability metrics
- Power market simulations
- Interactive Power BI deployment decision dashboard
