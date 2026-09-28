from pathlib import Path

import pandas as pd


# =============================================================================
# 1. PATHS
# =============================================================================

PROJECT_ROOT = Path(
    r"C:\Users\Hp\Industrial-Analytics"
    r"\NIST Robotic Work Cell Operational Analytics"
)

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "throughput_recovery_scenarios.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "benchmark_cost_per_part_analysis.csv"
)


# =============================================================================
# 2. PUBLIC BENCHMARK SOURCES
# =============================================================================

# -------------------------------------------------------------------------
# 2.1 U.S. BUREAU OF LABOR STATISTICS (BLS)
# -------------------------------------------------------------------------
#
# Source:
# U.S. Bureau of Labor Statistics
# Employer Costs for Employee Compensation
#
# Manufacturing industry, June 2026:
# Wages and salaries = $32.50/hour
# Benefits            = $16.12/hour
# Total compensation  = $48.62/hour
#
# IMPORTANT:
# This is a U.S. manufacturing-industry benchmark.
# It is NOT an observed labor cost from the NIST robotic work cell.

BLS_SOURCE_NAME = (
    "U.S. Bureau of Labor Statistics (BLS)"
)

BLS_SOURCE_TITLE = (
    "Employer Costs for Employee Compensation - "
    "Costs by Industry"
)

BLS_SOURCE_PERIOD = "June 2026"

BLS_SOURCE_URL = (
    "https://www.bls.gov/charts/"
    "employer-costs-for-employee-compensation/"
    "costs-by-industry.htm"
)

BLS_MANUFACTURING_WAGE_USD_HR = 32.50

BLS_MANUFACTURING_BENEFITS_USD_HR = 16.12

BLS_MANUFACTURING_COMPENSATION_USD_HR = (
    BLS_MANUFACTURING_WAGE_USD_HR
    + BLS_MANUFACTURING_BENEFITS_USD_HR
)


# =============================================================================
# 3. INDUSTRIAL ELECTRICITY BENCHMARK
# =============================================================================

# -------------------------------------------------------------------------
# 3.1 U.S. ENERGY INFORMATION ADMINISTRATION (EIA)
# -------------------------------------------------------------------------
#
# Source:
# U.S. Energy Information Administration
#
# 2025 U.S. average industrial electricity price:
# 8.62 cents/kWh
#
# Conversion:
# 8.62 cents/kWh / 100 = $0.0862/kWh
#
# IMPORTANT:
# This is a U.S. industrial electricity benchmark.
# It is NOT the measured electricity tariff paid by the NIST facility.

EIA_SOURCE_NAME = (
    "U.S. Energy Information Administration (EIA)"
)

EIA_SOURCE_TITLE = (
    "Electricity Prices and Factors Affecting Prices"
)

EIA_SOURCE_PERIOD = "2025 U.S. industrial average"

EIA_SOURCE_URL = (
    "https://www.eia.gov/energyexplained/"
    "electricity/prices-and-factors-affecting-prices.php"
)

EIA_INDUSTRIAL_ELECTRICITY_CENTS_KWH = 8.62

EIA_INDUSTRIAL_ELECTRICITY_USD_KWH = (
    EIA_INDUSTRIAL_ELECTRICITY_CENTS_KWH
    / 100
)


# =============================================================================
# 4. ROBOT POWER PROXIES
# =============================================================================

# -------------------------------------------------------------------------
# 4.1 UNIVERSAL ROBOTS
# -------------------------------------------------------------------------
#
# Manufacturer:
# Universal Robots
#
# Published typical-program power consumption used as proxy:
#
# UR3e = approximately 150 W
# UR5e = approximately 200 W
#
# Conversion:
# 150 W / 1000 = 0.150 kW
# 200 W / 1000 = 0.200 kW
#
# Combined proxy:
# 0.150 + 0.200 = 0.350 kW
#
# IMPORTANT:
# The NIST experiment used an older UR-series robotic setup.
# The published e-Series figures below are therefore EXTERNAL PROXIES.
#
# They are NOT measured electrical consumption from the NIST experiment.

UR_SOURCE_NAME = "Universal Robots"

UR3_SOURCE_TITLE = (
    "UR3e Technical Specifications"
)

UR3_SOURCE_URL = (
    "https://www.universal-robots.com/manuals/EN/HTML/"
    "SW10_8/Content/prod-usr-man/complianceUR3e/"
    "H_g5_sections/appendix_g5/tech_spec_data.htm"
)

UR5_SOURCE_TITLE = (
    "Universal Robots UR5e / e-Series "
    "published technical specifications"
)

UR5_SOURCE_URL = (
    "https://www.universal-robots.com/products/ur5-robot/"
)

UR3_PROXY_WATTS = 150.0
UR5_PROXY_WATTS = 200.0

UR3_PROXY_KW = (
    UR3_PROXY_WATTS
    / 1000
)

UR5_PROXY_KW = (
    UR5_PROXY_WATTS
    / 1000
)

TOTAL_ROBOT_PROXY_KW = (
    UR3_PROXY_KW
    + UR5_PROXY_KW
)


# =============================================================================
# 5. LABOR ALLOCATION SCENARIOS
# =============================================================================

# The NIST dataset does not state that a specific employee was continuously
# assigned to the robotic work cell.
#
# Therefore labor allocation is treated as a SCENARIO ASSUMPTION.
#
# 0.00 = no directly allocated labor in this narrow model
# 0.25 = quarter FTE-equivalent
# 0.50 = half FTE-equivalent
# 1.00 = one full FTE-equivalent
#
# These values are NOT observed staffing levels.

LABOR_FTE_SCENARIOS = [
    0.00,
    0.25,
    0.50,
    1.00,
]


# =============================================================================
# 6. LOAD THROUGHPUT SCENARIOS
# =============================================================================

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Input file not found:\n{INPUT_FILE}"
    )

df = pd.read_csv(INPUT_FILE)


required_columns = [
    "cycle_reduction_sec",
    "baseline_cycle_sec",
    "scenario_cycle_sec",
    "scenario_parts_per_hour",
    "throughput_gain_pct",
]

missing_columns = [
    col
    for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        "Required columns missing from input file: "
        f"{missing_columns}"
    )


print("=" * 80)
print("NIST ROBOTIC WORK CELL - BENCHMARK COST PER PART ANALYSIS")
print("=" * 80)

print(
    f"\nInput file:\n{INPUT_FILE}"
)

print(
    f"\nThroughput scenarios loaded: "
    f"{len(df):,}"
)


# =============================================================================
# 7. OBSERVED / PROJECT-DERIVED BASELINE
# =============================================================================

baseline_row = (
    df[
        df["cycle_reduction_sec"] == 0
    ]
    .iloc[0]
)

baseline_cycle_sec = float(
    baseline_row[
        "baseline_cycle_sec"
    ]
)

baseline_parts_per_hour = float(
    baseline_row[
        "scenario_parts_per_hour"
    ]
)


print("\n" + "=" * 80)
print("OBSERVED / PROJECT-DERIVED PRODUCTION BASELINE")
print("=" * 80)

print(
    f"\nBaseline production heartbeat: "
    f"{baseline_cycle_sec:.4f} sec/part"
)

print(
    f"Baseline throughput: "
    f"{baseline_parts_per_hour:.4f} parts/hour"
)

print(
    "\nClassification: "
    "OBSERVED / DERIVED FROM NIST PROJECT DATA"
)


# =============================================================================
# 8. DISPLAY PUBLIC BENCHMARK INPUTS
# =============================================================================

print("\n" + "=" * 80)
print("PUBLIC BENCHMARK INPUTS")
print("=" * 80)


# -----------------------------------------------------------------------------
# BLS
# -----------------------------------------------------------------------------

print("\nBLS MANUFACTURING LABOR BENCHMARK")

print(
    f"  Wages and salaries: "
    f"${BLS_MANUFACTURING_WAGE_USD_HR:.2f}/hour"
)

print(
    f"  Employer benefits: "
    f"${BLS_MANUFACTURING_BENEFITS_USD_HR:.2f}/hour"
)

print(
    f"  Total compensation: "
    f"${BLS_MANUFACTURING_COMPENSATION_USD_HR:.2f}/hour"
)

print(
    f"  Period: "
    f"{BLS_SOURCE_PERIOD}"
)

print(
    f"  Source: "
    f"{BLS_SOURCE_NAME}"
)

print(
    f"  URL: "
    f"{BLS_SOURCE_URL}"
)

print(
    "  Classification: PUBLIC BENCHMARK"
)


# -----------------------------------------------------------------------------
# EIA
# -----------------------------------------------------------------------------

print("\nEIA INDUSTRIAL ELECTRICITY BENCHMARK")

print(
    f"  Industrial electricity price: "
    f"{EIA_INDUSTRIAL_ELECTRICITY_CENTS_KWH:.2f} cents/kWh"
)

print(
    f"  Converted electricity price: "
    f"${EIA_INDUSTRIAL_ELECTRICITY_USD_KWH:.4f}/kWh"
)

print(
    f"  Period: "
    f"{EIA_SOURCE_PERIOD}"
)

print(
    f"  Source: "
    f"{EIA_SOURCE_NAME}"
)

print(
    f"  URL: "
    f"{EIA_SOURCE_URL}"
)

print(
    "  Classification: PUBLIC BENCHMARK"
)


# -----------------------------------------------------------------------------
# UNIVERSAL ROBOTS
# -----------------------------------------------------------------------------

print("\nUNIVERSAL ROBOTS POWER PROXIES")

print(
    f"  UR3e typical-program proxy: "
    f"{UR3_PROXY_WATTS:.0f} W "
    f"({UR3_PROXY_KW:.3f} kW)"
)

print(
    f"  UR5e typical-program proxy: "
    f"{UR5_PROXY_WATTS:.0f} W "
    f"({UR5_PROXY_KW:.3f} kW)"
)

print(
    f"  Combined robot power proxy: "
    f"{TOTAL_ROBOT_PROXY_KW:.3f} kW"
)

print(
    f"  UR3e source: "
    f"{UR_SOURCE_NAME}"
)

print(
    f"  UR3e URL: "
    f"{UR3_SOURCE_URL}"
)

print(
    f"  UR5e source: "
    f"{UR_SOURCE_NAME}"
)

print(
    f"  UR5e URL: "
    f"{UR5_SOURCE_URL}"
)

print(
    "  Classification: PUBLIC MANUFACTURER PROXY"
)


# =============================================================================
# 9. ROBOT ELECTRICITY-COST PROXY
# =============================================================================

robot_energy_cost_per_hour = (
    TOTAL_ROBOT_PROXY_KW
    * EIA_INDUSTRIAL_ELECTRICITY_USD_KWH
)


print("\n" + "=" * 80)
print("ROBOT ELECTRICITY-COST PROXY")
print("=" * 80)

print(
    f"\nCombined robot power proxy: "
    f"{TOTAL_ROBOT_PROXY_KW:.3f} kW"
)

print(
    f"Industrial electricity benchmark: "
    f"${EIA_INDUSTRIAL_ELECTRICITY_USD_KWH:.4f}/kWh"
)

print(
    f"Robot electricity-cost proxy: "
    f"${robot_energy_cost_per_hour:.4f}/hour"
)

print(
    "\nCalculation:"
)

print(
    f"  {TOTAL_ROBOT_PROXY_KW:.3f} kW"
    f" x "
    f"${EIA_INDUSTRIAL_ELECTRICITY_USD_KWH:.4f}/kWh"
    f" = "
    f"${robot_energy_cost_per_hour:.4f}/hour"
)

print(
    "\nIMPORTANT:"
)

print(
    "This represents only the two robot power proxies."
)

print(
    "It excludes PLCs, computers, tooling, lighting, HVAC, "
    "compressed air and other facility loads."
)


# =============================================================================
# 10. BUILD BENCHMARK COST-PER-PART SCENARIOS
# =============================================================================

rows = []

for labor_fte in LABOR_FTE_SCENARIOS:

    allocated_labor_cost_per_hour = (
        BLS_MANUFACTURING_COMPENSATION_USD_HR
        * labor_fte
    )

    benchmark_time_cost_per_hour = (
        allocated_labor_cost_per_hour
        + robot_energy_cost_per_hour
    )

    for _, scenario in df.iterrows():

        cycle_reduction_sec = float(
            scenario[
                "cycle_reduction_sec"
            ]
        )

        scenario_cycle_sec = float(
            scenario[
                "scenario_cycle_sec"
            ]
        )

        parts_per_hour = float(
            scenario[
                "scenario_parts_per_hour"
            ]
        )

        throughput_gain_pct = float(
            scenario[
                "throughput_gain_pct"
            ]
        )

        # ---------------------------------------------------------------------
        # Benchmark time-dependent cost per part
        #
        # Cost/part =
        # benchmark hourly time-dependent cost / parts per hour
        # ---------------------------------------------------------------------

        benchmark_cost_per_part = (
            benchmark_time_cost_per_hour
            / parts_per_hour
        )

        # ---------------------------------------------------------------------
        # Relative cost index
        #
        # Under a constant hourly-cost assumption:
        #
        # New time-dependent cost / baseline time-dependent cost
        # =
        # New cycle time / baseline cycle time
        # ---------------------------------------------------------------------

        relative_time_cost_index = (
            scenario_cycle_sec
            / baseline_cycle_sec
            * 100
        )

        relative_time_cost_reduction_pct = (
            100
            - relative_time_cost_index
        )

        rows.append(
            {
                # -------------------------------------------------------------
                # OBSERVED / PROJECT-DERIVED
                # -------------------------------------------------------------

                "baseline_cycle_sec":
                    baseline_cycle_sec,

                "baseline_parts_per_hour":
                    baseline_parts_per_hour,

                # -------------------------------------------------------------
                # SCENARIO ASSUMPTIONS / OUTPUT
                # -------------------------------------------------------------

                "cycle_reduction_sec":
                    cycle_reduction_sec,

                "scenario_cycle_sec":
                    scenario_cycle_sec,

                "scenario_parts_per_hour":
                    parts_per_hour,

                "throughput_gain_pct":
                    throughput_gain_pct,

                # -------------------------------------------------------------
                # LABOR BENCHMARK
                # -------------------------------------------------------------

                "labor_fte_assumption":
                    labor_fte,

                "bls_wage_usd_hr":
                    BLS_MANUFACTURING_WAGE_USD_HR,

                "bls_benefits_usd_hr":
                    BLS_MANUFACTURING_BENEFITS_USD_HR,

                "bls_total_compensation_usd_hr":
                    BLS_MANUFACTURING_COMPENSATION_USD_HR,

                "allocated_labor_cost_usd_hr":
                    allocated_labor_cost_per_hour,

                # -------------------------------------------------------------
                # ENERGY BENCHMARK / PROXY
                # -------------------------------------------------------------

                "ur3_power_proxy_kw":
                    UR3_PROXY_KW,

                "ur5_power_proxy_kw":
                    UR5_PROXY_KW,

                "combined_robot_power_proxy_kw":
                    TOTAL_ROBOT_PROXY_KW,

                "electricity_benchmark_usd_kwh":
                    EIA_INDUSTRIAL_ELECTRICITY_USD_KWH,

                "robot_energy_cost_proxy_usd_hr":
                    robot_energy_cost_per_hour,

                # -------------------------------------------------------------
                # BENCHMARK SCENARIO ECONOMICS
                # -------------------------------------------------------------

                "benchmark_time_cost_usd_hr":
                    benchmark_time_cost_per_hour,

                "benchmark_time_cost_per_part_usd":
                    benchmark_cost_per_part,

                "relative_time_cost_index":
                    relative_time_cost_index,

                "relative_time_cost_reduction_pct":
                    relative_time_cost_reduction_pct,

                # -------------------------------------------------------------
                # SOURCE TRACEABILITY
                # -------------------------------------------------------------

                "labor_source_name":
                    BLS_SOURCE_NAME,

                "labor_source_title":
                    BLS_SOURCE_TITLE,

                "labor_source_period":
                    BLS_SOURCE_PERIOD,

                "labor_source_url":
                    BLS_SOURCE_URL,

                "electricity_source_name":
                    EIA_SOURCE_NAME,

                "electricity_source_title":
                    EIA_SOURCE_TITLE,

                "electricity_source_period":
                    EIA_SOURCE_PERIOD,

                "electricity_source_url":
                    EIA_SOURCE_URL,

                "ur3_power_source_name":
                    UR_SOURCE_NAME,

                "ur3_power_source_title":
                    UR3_SOURCE_TITLE,

                "ur3_power_source_url":
                    UR3_SOURCE_URL,

                "ur5_power_source_name":
                    UR_SOURCE_NAME,

                "ur5_power_source_title":
                    UR5_SOURCE_TITLE,

                "ur5_power_source_url":
                    UR5_SOURCE_URL,

                # -------------------------------------------------------------
                # CLASSIFICATION
                # -------------------------------------------------------------

                "production_metric_classification":
                    "OBSERVED / PROJECT-DERIVED",

                "labor_input_classification":
                    "PUBLIC BENCHMARK",

                "electricity_input_classification":
                    "PUBLIC BENCHMARK",

                "robot_power_input_classification":
                    "PUBLIC MANUFACTURER PROXY",

                "labor_fte_classification":
                    "SCENARIO ASSUMPTION",

                "cost_output_classification":
                    "BENCHMARK SCENARIO OUTPUT",
            }
        )


cost_df = pd.DataFrame(rows)


# =============================================================================
# 11. RELATIVE TIME-DEPENDENT COST EFFECT
# =============================================================================

print("\n" + "=" * 80)
print("RELATIVE TIME-DEPENDENT COST PER PART")
print("=" * 80)

relative_table = (
    cost_df[
        [
            "cycle_reduction_sec",
            "scenario_cycle_sec",
            "scenario_parts_per_hour",
            "throughput_gain_pct",
            "relative_time_cost_index",
            "relative_time_cost_reduction_pct",
        ]
    ]
    .drop_duplicates()
    .sort_values(
        "cycle_reduction_sec"
    )
)

print(
    relative_table
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 12. BENCHMARK COST PER PART BY LABOR ALLOCATION
# =============================================================================

print("\n" + "=" * 80)
print("BENCHMARK COST PER PART BY LABOR ALLOCATION")
print("=" * 80)

display_cols = [
    "cycle_reduction_sec",
    "labor_fte_assumption",
    "scenario_parts_per_hour",
    "allocated_labor_cost_usd_hr",
    "robot_energy_cost_proxy_usd_hr",
    "benchmark_time_cost_usd_hr",
    "benchmark_time_cost_per_part_usd",
    "relative_time_cost_reduction_pct",
]

print(
    cost_df[
        display_cols
    ]
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 13. BASELINE BENCHMARK COST PER PART
# =============================================================================

print("\n" + "=" * 80)
print("BASELINE BENCHMARK COST PER PART")
print("=" * 80)

baseline_cost = (
    cost_df[
        cost_df[
            "cycle_reduction_sec"
        ] == 0
    ][
        [
            "labor_fte_assumption",
            "allocated_labor_cost_usd_hr",
            "robot_energy_cost_proxy_usd_hr",
            "benchmark_time_cost_usd_hr",
            "benchmark_time_cost_per_part_usd",
        ]
    ]
    .copy()
)

print(
    baseline_cost
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 14. FIVE-SECOND CYCLE-REDUCTION EXAMPLE
# =============================================================================

print("\n" + "=" * 80)
print("5-SECOND CYCLE-REDUCTION SCENARIO")
print("=" * 80)

five_sec = (
    cost_df[
        cost_df[
            "cycle_reduction_sec"
        ] == 5
    ]
    .copy()
)

five_sec_rows = []

for _, row in five_sec.iterrows():

    labor_fte = float(
        row[
            "labor_fte_assumption"
        ]
    )

    baseline_match = (
        cost_df[
            (
                cost_df[
                    "cycle_reduction_sec"
                ] == 0
            )
            &
            (
                cost_df[
                    "labor_fte_assumption"
                ] == labor_fte
            )
        ]
        .iloc[0]
    )

    baseline_cpp = float(
        baseline_match[
            "benchmark_time_cost_per_part_usd"
        ]
    )

    scenario_cpp = float(
        row[
            "benchmark_time_cost_per_part_usd"
        ]
    )

    saving_per_part = (
        baseline_cpp
        - scenario_cpp
    )

    saving_per_1000_parts = (
        saving_per_part
        * 1000
    )

    five_sec_rows.append(
        {
            "labor_fte_assumption":
                labor_fte,

            "baseline_cost_per_part_usd":
                baseline_cpp,

            "scenario_cost_per_part_usd":
                scenario_cpp,

            "benchmark_saving_per_part_usd":
                saving_per_part,

            "benchmark_saving_per_1000_parts_usd":
                saving_per_1000_parts,

            "relative_cost_reduction_pct":
                row[
                    "relative_time_cost_reduction_pct"
                ],
        }
    )


five_sec_summary = pd.DataFrame(
    five_sec_rows
)

print(
    five_sec_summary
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 15. BENCHMARK COST FOR 1,000 PARTS
# =============================================================================

print("\n" + "=" * 80)
print("BENCHMARK TIME-DEPENDENT COST FOR 1,000 PARTS")
print("=" * 80)

volume_rows = []

for _, row in cost_df.iterrows():

    benchmark_cost_1000 = (
        row[
            "benchmark_time_cost_per_part_usd"
        ]
        * 1000
    )

    volume_rows.append(
        {
            "cycle_reduction_sec":
                row[
                    "cycle_reduction_sec"
                ],

            "labor_fte_assumption":
                row[
                    "labor_fte_assumption"
                ],

            "scenario_parts_per_hour":
                row[
                    "scenario_parts_per_hour"
                ],

            "benchmark_cost_per_part_usd":
                row[
                    "benchmark_time_cost_per_part_usd"
                ],

            "benchmark_cost_1000_parts_usd":
                benchmark_cost_1000,
        }
    )


volume_df = pd.DataFrame(
    volume_rows
)

print(
    volume_df
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 16. PUBLIC-SOURCE REFERENCE TABLE
# =============================================================================

print("\n" + "=" * 80)
print("PUBLIC-SOURCE REFERENCES")
print("=" * 80)

reference_table = pd.DataFrame(
    [
        {
            "input":
                "Manufacturing labor compensation",

            "value_used":
                (
                    f"${BLS_MANUFACTURING_COMPENSATION_USD_HR:.2f}/hour"
                ),

            "source":
                BLS_SOURCE_NAME,

            "period":
                BLS_SOURCE_PERIOD,

            "classification":
                "PUBLIC BENCHMARK",

            "url":
                BLS_SOURCE_URL,
        },
        {
            "input":
                "Industrial electricity",

            "value_used":
                (
                    f"${EIA_INDUSTRIAL_ELECTRICITY_USD_KWH:.4f}/kWh"
                ),

            "source":
                EIA_SOURCE_NAME,

            "period":
                EIA_SOURCE_PERIOD,

            "classification":
                "PUBLIC BENCHMARK",

            "url":
                EIA_SOURCE_URL,
        },
        {
            "input":
                "UR3 robot power",

            "value_used":
                (
                    f"{UR3_PROXY_WATTS:.0f} W"
                ),

            "source":
                UR_SOURCE_NAME,

            "period":
                "Published specification",

            "classification":
                "PUBLIC MANUFACTURER PROXY",

            "url":
                UR3_SOURCE_URL,
        },
        {
            "input":
                "UR5 robot power",

            "value_used":
                (
                    f"{UR5_PROXY_WATTS:.0f} W"
                ),

            "source":
                UR_SOURCE_NAME,

            "period":
                "Published specification",

            "classification":
                "PUBLIC MANUFACTURER PROXY",

            "url":
                UR5_SOURCE_URL,
        },
    ]
)

print(
    reference_table.to_string(
        index=False
    )
)


# =============================================================================
# 17. EVIDENCE CLASSIFICATION
# =============================================================================

print("\n" + "=" * 80)
print("EVIDENCE CLASSIFICATION")
print("=" * 80)

evidence = pd.DataFrame(
    [
        {
            "item":
                "Production heartbeat / throughput",

            "classification":
                "OBSERVED / PROJECT-DERIVED",

            "meaning":
                "Derived from NIST process-event data",
        },
        {
            "item":
                "Cycle reductions of 0-5 seconds",

            "classification":
                "SCENARIO ASSUMPTION",

            "meaning":
                "Hypothetical operational improvements",
        },
        {
            "item":
                "Manufacturing compensation",

            "classification":
                "PUBLIC BENCHMARK",

            "meaning":
                "BLS U.S. manufacturing compensation",
        },
        {
            "item":
                "Industrial electricity price",

            "classification":
                "PUBLIC BENCHMARK",

            "meaning":
                "EIA U.S. industrial electricity average",
        },
        {
            "item":
                "UR3e / UR5e power",

            "classification":
                "PUBLIC MANUFACTURER PROXY",

            "meaning":
                "Published Universal Robots specifications",
        },
        {
            "item":
                "Labor FTE allocation",

            "classification":
                "SCENARIO ASSUMPTION",

            "meaning":
                "Not observed in NIST dataset",
        },
        {
            "item":
                "Benchmark cost per part",

            "classification":
                "BENCHMARK SCENARIO OUTPUT",

            "meaning":
                "Not actual NIST accounting cost",
        },
    ]
)

print(
    evidence.to_string(
        index=False
    )
)


# =============================================================================
# 18. SAVE OUTPUT
# =============================================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

cost_df.to_csv(
    OUTPUT_FILE,
    index=False,
)


# =============================================================================
# 19. OUTPUT SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("OUTPUT")
print("=" * 80)

print(
    f"\nSaved:\n{OUTPUT_FILE}"
)

print(
    f"\nOutput shape: "
    f"{cost_df.shape}"
)


# =============================================================================
# 20. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
This analysis does NOT estimate the actual accounting cost of producing
a part in the NIST robotic work cell.

The evidence is deliberately separated into four categories:

1. OBSERVED / PROJECT-DERIVED
   Production cycle time and throughput are derived from the NIST
   process-event dataset analysed in this project.

2. PUBLIC BENCHMARKS
   Manufacturing labor compensation is sourced from the U.S. Bureau
   of Labor Statistics (BLS).

   Industrial electricity pricing is sourced from the U.S. Energy
   Information Administration (EIA).

3. PUBLIC MANUFACTURER PROXIES
   Robot power values are based on published Universal Robots e-Series
   specifications. They are used only as proxies and are not measured
   power consumption from the NIST experiment.

4. SCENARIO ASSUMPTIONS
   Cycle-time reductions and labor FTE allocations are hypothetical
   analytical scenarios rather than observed operational changes.

The resulting dollar values are therefore BENCHMARK-ASSISTED SCENARIO
ECONOMICS. They must not be interpreted as the actual accounting cost
of the NIST robotic work cell.

The most assumption-light economic result is the relative change in
the time-dependent cost component per part.

Under a constant hourly-cost assumption:

    relative cost per part
        = scenario cycle time / baseline cycle time

Therefore reducing the production heartbeat reduces the allocation of
time-dependent operating cost to each produced part.

The model intentionally excludes:

- material cost,
- tooling cost,
- maintenance,
- robot depreciation,
- PLC and computer electricity,
- facility overhead,
- HVAC,
- compressed air,
- quality losses,
- financing costs,
- downtime cost,
- and other manufacturing expenses.

Those categories are excluded because defensible cell-specific values
are not available from the NIST source dataset.

This prevents external assumptions from being presented as measured
NIST manufacturing costs.
"""
)