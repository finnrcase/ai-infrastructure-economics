# Power, Compute, and Geography:
## A Quantitative Framework for AI Infrastructure Competitiveness

---

# Abstract

In prog

---

# Research Question

How do electricity markets, infrastructure characteristics, and power constraints influence AI infrastructure competitiveness?

---

# Methodology

This study uses a quantitative framework to evaluate the competitiveness of U.S. states as locations for AI infrastructure. Rather than attempting to predict specific locations for future data centers, the goal of the research is to compare states using a consistent set of energy, infrastructure, and ecosystem characteristics that are most likely to have a large influence on AI infrastructure investment decisions.

The analysis has three main components:

- Regional Competitiveness Framework
- Monte Carlo Robustness Analysis
- Behind-the-Meter Infrastructure Economics

---

## State Sample Selection

The model uses 15 states that are currently most considered for potential AI infrastructure growth markets.

- Texas
- Virginia
- Arizona
- California
- Nevada
- Georgia
- Ohio
- Oregon
- Washington
- North Carolina
- Utah
- Tennessee
- Indiana
- Pennsylvania
- Illinois

---

## Variables

Version 1 uses six variables:

### Electricity Price
Industrial electricity prices collected from the U.S. Energy Information Administration (EIA).

### Grid Capacity
Installed generation capacity collected from the EIA.

### Renewable Energy Share
Percentage of electricity generated from renewable sources collected from the EIA.

### Ecosystem Score
Current data center counts obtained from DataCenterMap.

### Behind-the-Meter Score
A proxy measure of behind-the-meter deployment potential derived from state-level natural gas generation characteristics. This variable is used in the competitiveness framework to estimate the relative attractiveness of states for behind-the-meter development. It is distinct from the separate Behind-the-Meter Economics Framework, which directly models the cost of grid, natural gas, solar, and hybrid power architectures.

### Interconnection Friction Score
Because state-level queue duration data was not consistently available, a regional proxy approach was used. States were assigned scores based on the relative difficulty of transmission interconnection within their primary interconnection region.

---

# Regional Competitiveness Framework

The normalized variables were combined into a weighted competitiveness score representing the relative attractiveness of each state for future AI infrastructure deployment.

Weighting was based on sourced information about industry.

---

# Monte Carlo Robustness Analysis

Because of the use of subjective weighting assumptions, a Monte Carlo simulation framework was added.

### 10,000 Simulations

For each simulation:

1. Variable weights were randomly generated using a Dirichlet distribution.
2. Competitiveness scores were recalculated.
3. States were ranked according to their simulated score.

The Monte Carlo framework was used to estimate:

- Winner Frequency
- Top-Three Frequency
- Median Competitiveness
- Competitiveness Volatility

---

# Behind-the-Meter Infrastructure Economics

Six of the high-performing states were used:

- Texas
- Virginia
- Arizona
- California
- Nevada
- Washington

The framework evaluates:

## Grid Power

Electricity purchased entirely from the grid using state-level industrial electricity prices.

## Natural Gas Generation

Behind-the-meter generation using state-level natural gas prices and simplified generation cost assumptions.

## Solar Generation

Utility-scale solar generation using capacity factors estimated from NREL PVWatts simulations.

## Hybrid Systems

A simplified hybrid architecture combining solar generation, battery storage, and natural gas backup generation. This is the most realistic model since it incorporates a factor not explicitly captured by the competitiveness framework: reliability.

The objective is to identify which power architecture minimizes electricity costs under different regional conditions.

---

# Main Findings

In Progress

---

# Research Question

How do electricity markets, infrastructure characteristics, and power constraints influence AI infrastructure competitiveness across the United States?

---

# Contributions

Most research on the expansion of AI electricity demand evaluates environmental impacts, policy tradeoffs, or AI model growth. This paper focuses on AI infrastructure economics through a bottom-up framework designed to evaluate regional competitiveness and emerging infrastructure strategies used to attract investment in AI expansion.

The framework models how electricity pricing, grid capacity, infrastructure constraints, interconnection conditions, and energy generation availability influence where AI infrastructure is likely to be constructed. Using scenario analysis and Monte Carlo simulations, the paper quantifies uncertainty while identifying the factors that drive future competitiveness.

Beyond evaluating infrastructure competitiveness, the framework also examines the emergence of behind-the-meter power solutions, including natural gas, solar, and hybrid power systems as potential responses to growing power constraints associated with AI expansion.

---

# Sources by Research Component

## 1. Regional Competitiveness Framework

### Electricity Markets and Power System Data

United States Energy Information Administration. “U.S. States.” U.S. Energy Information Administration, https://www.eia.gov/state/.

United States Energy Information Administration. “Electricity Data Browser.” U.S. Energy Information Administration, https://www.eia.gov/electricity/data.php.

United States Energy Information Administration. Electric Power Monthly. U.S. Energy Information Administration, https://www.eia.gov/electricity/monthly/.

### Infrastructure Ecosystem Data

Data Center Map. “Data Center Locations in the United States.” Data Center Map, https://www.datacentermap.com/usa/.

### Interconnection Friction and Queue Constraints

Rand, Joseph, et al. Queued Up: 2025 Edition—Characteristics of Power Plants Seeking Transmission Interconnection As of the End of 2024. Lawrence Berkeley National Laboratory, Dec. 2025, https://emp.lbl.gov/queues.

Lawrence Berkeley National Laboratory. “Interconnection Queue Data and Reports.” Lawrence Berkeley National Laboratory, 2025.

PJM Interconnection. “Interconnection Process Reform and Queue Statistics.” PJM Interconnection, 2025.

California Independent System Operator. “Interconnection Queue Management and Transmission Planning Reports.” CAISO, 2025.

Midcontinent Independent System Operator. “Generator Interconnection Queue Reports.” MISO, 2025.

Electric Reliability Council of Texas. “Generation Interconnection Status Reports.” ERCOT, 2025.

---

## 2. Behind-the-Meter Economics Framework

### Electricity Prices

United States Energy Information Administration. “U.S. States.” U.S. Energy Information Administration, https://www.eia.gov/state/.

### Natural Gas Prices

United States Energy Information Administration. “U.S. States.” U.S. Energy Information Administration, https://www.eia.gov/state/.

### Solar Resource Estimates

National Renewable Energy Laboratory. “PVWatts Calculator.” National Renewable Energy Laboratory, https://pvwatts.nrel.gov/pvwatts.php.

---

## 3. Literature Review and Industry Context

### AI Infrastructure and Energy Demand

International Energy Agency. Energy and AI. International Energy Agency, https://www.iea.org/reports/energy-and-ai.

Electric Power Research Institute. “Powering Intelligence: Analyzing Artificial Intelligence and Data Center Energy Consumption.” EPRI, https://powering-intelligence.epri.com/executive-summary.html.

Lawrence Berkeley National Laboratory. 2024 LBNL Data Center Energy Usage Report. Lawrence Berkeley National Laboratory, https://eta.lbl.gov/publications/2024-lbnl-data-center-energy-usage-report.

United States Department of Energy. “Clean Energy Resources to Meet Data Center Electricity Demand.” U.S. Department of Energy, https://www.energy.gov/oe/clean-energy-resources-meet-data-center-electricity-demand.

Uptime Institute. “Power Usage Effectiveness (PUE).” Uptime Institute, https://uptimeinstitute.com/pue.

---

## 4. Industry Strategy and Infrastructure Development

Amazon Web Services. “AWS Sustainability.” Amazon Web Services, https://sustainability.aboutamazon.com/environment/the-cloud?energyType=true.

Google. “Data Center Sustainability.” Google Data Centers, https://www.google.com/about/datacenters/sustainability/.

Meta. “Data Center Sustainability.” Meta Sustainability, https://sustainability.atmeta.com/data-centers/.

Microsoft. “Microsoft Sustainability.” Microsoft, https://www.microsoft.com/en-us/sustainability.

NVIDIA. “NVIDIA H100 Tensor Core GPU.” NVIDIA, https://www.nvidia.com/en-us/data-center/h100/.

NVIDIA. “NVIDIA Blackwell Architecture.” NVIDIA, https://www.nvidia.com/en-us/data-center/technologies/blackwell-architecture/.