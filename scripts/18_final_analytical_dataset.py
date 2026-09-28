from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# 1. PATHS
# =============================================================================

PROJECT_ROOT = Path(
    r"C:\Users\Hp\Industrial-Analytics"
    r"\NIST Robotic Work Cell Operational Analytics"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)


# -----------------------------------------------------------------------------
# Validated analytical outputs produced by earlier scripts
# -----------------------------------------------------------------------------

PARTDATA_FILE = (
    PROCESSED_DIR
    / "partdata_normalized.csv"
)

CYCLE_STAGE_FILE = (
    PROCESSED_DIR
    / "cycle_stage_durations.csv"
)

BOTTLENECK_FILE = (
    PROCESSED_DIR
    / "bottleneck_cycle_decomposition.csv"
)

ROBOT_SIGNATURE_FILE = (
    PROCESSED_DIR
    / "robot_motion_signature_analysis.csv"
)

THROUGHPUT_FILE = (
    PROCESSED_DIR
    / "throughput_recovery_scenarios.csv"
)

BENCHMARK_COST_FILE = (
    PROCESSED_DIR
    / "benchmark_cost_per_part_analysis.csv"
)


# -----------------------------------------------------------------------------
# Final analytical outputs
# -----------------------------------------------------------------------------

FINAL_KPI_FILE = (
    OUTPUT_DIR
    / "final_operational_kpis.csv"
)

FINAL_SCENARIO_FILE = (
    OUTPUT_DIR
    / "final_throughput_cost_scenarios.csv"
)

FINAL_EVIDENCE_FILE = (
    OUTPUT_DIR
    / "final_evidence_register.csv"
)


# =============================================================================
# 2. HELPER FUNCTIONS
# =============================================================================

def load_required_csv(path, label):
    """
    Load a required analytical output.

    The script stops rather than silently continuing if an expected
    upstream analytical file is missing.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"{label} not found:\n{path}"
        )

    df = pd.read_csv(path)

    print(
        f"{label:<38} "
        f"shape={df.shape}"
    )

    return df


def require_columns(df, columns, label):
    """
    Validate that expected columns exist before calculations are made.
    """

    missing = [
        col
        for col in columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{label} is missing required columns: "
            f"{missing}"
        )


def add_kpi(
    rows,
    kpi_name,
    value,
    unit,
    evidence_class,
    source_layer,
    interpretation,
):
    """
    Append one KPI to the final KPI register.
    """

    rows.append(
        {
            "kpi_name": kpi_name,
            "value": value,
            "unit": unit,
            "evidence_class": evidence_class,
            "source_layer": source_layer,
            "interpretation": interpretation,
        }
    )


# =============================================================================
# 3. LOAD VALIDATED UPSTREAM OUTPUTS
# =============================================================================

print("=" * 90)
print("NIST ROBOTIC WORK CELL - FINAL ANALYTICAL DATASET")
print("=" * 90)

print("\nLOADING VALIDATED ANALYTICAL OUTPUTS")
print("-" * 90)

partdata = load_required_csv(
    PARTDATA_FILE,
    "PartData normalized",
)

cycle_stage = load_required_csv(
    CYCLE_STAGE_FILE,
    "Cycle-stage analysis",
)

bottleneck = load_required_csv(
    BOTTLENECK_FILE,
    "Bottleneck decomposition",
)

robot_signature = load_required_csv(
    ROBOT_SIGNATURE_FILE,
    "Robot motion signatures",
)

throughput = load_required_csv(
    THROUGHPUT_FILE,
    "Throughput scenarios",
)

benchmark_cost = load_required_csv(
    BENCHMARK_COST_FILE,
    "Benchmark cost scenarios",
)


# =============================================================================
# 4. VALIDATE CORE INPUT STRUCTURE
# =============================================================================

require_columns(
    partdata,
    [
        "cycle_id",
    ],
    "PartData",
)

require_columns(
    throughput,
    [
        "cycle_reduction_sec",
        "baseline_cycle_sec",
        "scenario_cycle_sec",
        "scenario_parts_per_hour",
        "throughput_gain_pct",
    ],
    "Throughput scenarios",
)

require_columns(
    benchmark_cost,
    [
        "cycle_reduction_sec",
        "labor_fte_assumption",
        "scenario_parts_per_hour",
        "benchmark_time_cost_per_part_usd",
        "relative_time_cost_reduction_pct",
    ],
    "Benchmark cost scenarios",
)


# =============================================================================
# 5. CORE OBSERVED PRODUCTION KPIs
# =============================================================================

print("\n" + "=" * 90)
print("CORE OBSERVED / PROJECT-DERIVED KPIs")
print("=" * 90)


# -----------------------------------------------------------------------------
# Number of completed experimental parts
# -----------------------------------------------------------------------------

parts_observed = int(
    partdata["cycle_id"].nunique()
)


# -----------------------------------------------------------------------------
# Baseline production heartbeat and throughput
#
# These values were already established by the validated throughput analysis.
# The zero-reduction row is the observed baseline.
# -----------------------------------------------------------------------------

baseline_rows = throughput[
    throughput[
        "cycle_reduction_sec"
    ] == 0
].copy()

if len(baseline_rows) != 1:
    raise ValueError(
        "Expected exactly one zero-reduction baseline row "
        "in throughput scenarios."
    )

baseline_row = baseline_rows.iloc[0]

baseline_cycle_sec = float(
    baseline_row[
        "baseline_cycle_sec"
    ]
)

baseline_throughput_pph = float(
    baseline_row[
        "scenario_parts_per_hour"
    ]
)


# -----------------------------------------------------------------------------
# Capacity-setting task-process timing
#
# Earlier validation established the central steady-state t6 -> t9
# process at approximately 44.3264 seconds.
#
# Rather than hard-code that result, reconstruct it from the bottleneck
# decomposition where possible.
# -----------------------------------------------------------------------------

bottleneck_columns = set(
    bottleneck.columns
)

task_process_candidates = [
    "task_process_sec",
    "task_process_duration_sec",
    "task_process",
]

task_process_column = next(
    (
        col
        for col in task_process_candidates
        if col in bottleneck_columns
    ),
    None,
)

if task_process_column is not None:

    capacity_setting_process_sec = float(
        bottleneck[
            task_process_column
        ].mean()
    )

    capacity_setting_source = (
        f"Mean {task_process_column} from "
        "bottleneck_cycle_decomposition.csv"
    )

else:

    # Script 12 stores task-action and gap decomposition.
    # If the complete t6 -> t9 duration is not available in that file,
    # use the validated result from Script 15 rather than inventing a
    # reconstruction from incompatible boundaries.

    capacity_setting_process_sec = 44.3264

    capacity_setting_source = (
        "Validated Script 15 t6-to-t9 task-process result"
    )


# -----------------------------------------------------------------------------
# Task action component
# -----------------------------------------------------------------------------

task_action_candidates = [
    "task_action_sec",
    "task_action_duration_sec",
    "task_action",
]

task_action_column = next(
    (
        col
        for col in task_action_candidates
        if col in bottleneck_columns
    ),
    None,
)

if task_action_column is not None:

    task_action_sec = float(
        bottleneck[
            task_action_column
        ].mean()
    )

else:

    task_action_sec = 36.9369


# -----------------------------------------------------------------------------
# Recurring inter-task transition component
# -----------------------------------------------------------------------------

gap_candidates = [
    "gap_sec",
    "transition_gap_sec",
    "complete_to_next_start_sec",
]

gap_column = next(
    (
        col
        for col in gap_candidates
        if col in bottleneck_columns
    ),
    None,
)

if gap_column is not None:

    transition_gap_sec = float(
        bottleneck[
            gap_column
        ].mean()
    )

else:

    transition_gap_sec = 7.3869


task_action_share_pct = (
    task_action_sec
    / baseline_cycle_sec
    * 100
)

transition_gap_share_pct = (
    transition_gap_sec
    / baseline_cycle_sec
    * 100
)


print(
    f"\nExperimental parts observed: "
    f"{parts_observed}"
)

print(
    f"Baseline production heartbeat: "
    f"{baseline_cycle_sec:.4f} sec/part"
)

print(
    f"Baseline throughput: "
    f"{baseline_throughput_pph:.4f} parts/hour"
)

print(
    f"Validated task-process cycle: "
    f"{capacity_setting_process_sec:.4f} sec"
)

print(
    f"Task-action component: "
    f"{task_action_sec:.4f} sec"
)

print(
    f"Recurring transition component: "
    f"{transition_gap_sec:.4f} sec"
)

print(
    f"Task-action share of heartbeat: "
    f"{task_action_share_pct:.2f}%"
)

print(
    f"Transition share of heartbeat: "
    f"{transition_gap_share_pct:.2f}%"
)


# =============================================================================
# 6. ROBOT-MOTION EVIDENCE
# =============================================================================

print("\n" + "=" * 90)
print("DUAL-ROBOT MOTION EVIDENCE")
print("=" * 90)

print(
    "\nRobot-motion signatures are retained as supporting evidence."
)

print(
    "Stage-level motion dominance is NOT interpreted automatically "
    "as task ownership because the work cell is pipelined."
)

print(
    "\nValidated working interpretation:"
)

print(
    "  UR5 -> material-handling role strongly supported by input/output "
    "transfer motion."
)

print(
    "  UR3 -> task/drawing role supported by task-boundary motion, "
    "especially post-task behavior."
)

print(
    "  Role mapping remains an empirical interpretation rather than "
    "a directly documented source-data label."
)


# =============================================================================
# 7. BUILD FINAL KPI REGISTER
# =============================================================================

kpi_rows = []


add_kpi(
    kpi_rows,
    "Experimental Parts Observed",
    parts_observed,
    "parts",
    "OBSERVED",
    "NIST PartData",
    (
        "Number of unique production cycles represented "
        "in the experiment."
    ),
)

add_kpi(
    kpi_rows,
    "Baseline Production Heartbeat",
    baseline_cycle_sec,
    "seconds per part",
    "PROJECT-DERIVED",
    "Steady-state PartRemoved cadence",
    (
        "Observed steady-state production cadence used as "
        "the baseline for throughput scenarios."
    ),
)

add_kpi(
    kpi_rows,
    "Baseline Throughput",
    baseline_throughput_pph,
    "parts per hour",
    "PROJECT-DERIVED",
    "Steady-state PartRemoved cadence",
    (
        "Production-rate equivalent of the observed "
        "steady-state heartbeat."
    ),
)

add_kpi(
    kpi_rows,
    "Capacity-Setting Task Process",
    capacity_setting_process_sec,
    "seconds",
    "PROJECT-DERIVED",
    capacity_setting_source,
    (
        "t6-to-t9 task-process timing closely synchronized "
        "with the production heartbeat."
    ),
)

add_kpi(
    kpi_rows,
    "Task Action",
    task_action_sec,
    "seconds",
    "PROJECT-DERIVED",
    "Bottleneck decomposition",
    (
        "Core task-action component within the recurring "
        "capacity-setting process."
    ),
)

add_kpi(
    kpi_rows,
    "Recurring Transition",
    transition_gap_sec,
    "seconds",
    "PROJECT-DERIVED",
    "Bottleneck decomposition",
    (
        "Repeatable transition sequence between successive "
        "task starts; not automatically classified as waste."
    ),
)

add_kpi(
    kpi_rows,
    "Task Action Share of Production Heartbeat",
    task_action_share_pct,
    "percent",
    "CALCULATED",
    "Bottleneck decomposition",
    (
        "Task-action duration expressed relative to the "
        "steady-state production heartbeat."
    ),
)

add_kpi(
    kpi_rows,
    "Transition Share of Production Heartbeat",
    transition_gap_share_pct,
    "percent",
    "CALCULATED",
    "Bottleneck decomposition",
    (
        "Recurring transition duration expressed relative "
        "to the steady-state production heartbeat."
    ),
)


final_kpis = pd.DataFrame(
    kpi_rows
)


# =============================================================================
# 8. BUILD CONSOLIDATED THROUGHPUT + COST SCENARIO DATASET
# =============================================================================

print("\n" + "=" * 90)
print("CONSOLIDATING THROUGHPUT AND COST SCENARIOS")
print("=" * 90)


# -----------------------------------------------------------------------------
# Keep the operational scenario table as the base.
# -----------------------------------------------------------------------------

scenario = throughput.copy()


# -----------------------------------------------------------------------------
# Add time recovery per 1,000 parts if it is not already present.
#
# Every second removed from one production cycle saves the same number
# of seconds per produced part under the scenario assumption.
# -----------------------------------------------------------------------------

if "time_recovered_min_per_1000_parts" not in scenario.columns:

    scenario[
        "time_recovered_min_per_1000_parts"
    ] = (
        scenario[
            "cycle_reduction_sec"
        ]
        * 1000
        / 60
    )


# -----------------------------------------------------------------------------
# Add additional capacity over common operating horizons if not already
# available from Script 16.
# -----------------------------------------------------------------------------

for hours in [8, 12, 24]:

    col = (
        f"additional_parts_{hours}h"
    )

    if col not in scenario.columns:

        scenario[col] = (
            (
                scenario[
                    "scenario_parts_per_hour"
                ]
                - baseline_throughput_pph
            )
            * hours
        )


# -----------------------------------------------------------------------------
# Add the relative time-dependent cost result.
#
# This result does not require an FTE choice because under a constant
# hourly-cost assumption the relative cost per part follows the cycle-time
# ratio.
# -----------------------------------------------------------------------------

relative_cost = (
    benchmark_cost[
        [
            "cycle_reduction_sec",
            "relative_time_cost_reduction_pct",
        ]
    ]
    .drop_duplicates()
)

scenario = scenario.merge(
    relative_cost,
    on="cycle_reduction_sec",
    how="left",
    validate="one_to_one",
)


# -----------------------------------------------------------------------------
# Add selected benchmark cost scenarios.
#
# We preserve all labor assumptions in a separate long-form table below.
# The main scenario table remains operationally clean.
# -----------------------------------------------------------------------------

scenario[
    "scenario_classification"
] = "SCENARIO OUTPUT"

scenario[
    "baseline_metric_classification"
] = "OBSERVED / PROJECT-DERIVED"

scenario[
    "economic_interpretation"
] = (
    "Relative time-dependent cost effect under constant hourly-cost assumption"
)


# =============================================================================
# 9. CREATE LONG-FORM FINAL THROUGHPUT + COST TABLE
# =============================================================================

cost_columns = [
    "cycle_reduction_sec",
    "labor_fte_assumption",
    "allocated_labor_cost_usd_hr",
    "robot_energy_cost_proxy_usd_hr",
    "benchmark_time_cost_usd_hr",
    "benchmark_time_cost_per_part_usd",
    "relative_time_cost_reduction_pct",
]

require_columns(
    benchmark_cost,
    cost_columns,
    "Benchmark cost scenarios",
)


cost_long = benchmark_cost[
    cost_columns
].copy()


# Avoid duplicate relative-cost field when merging.
operational_for_merge = scenario.drop(
    columns=[
        "relative_time_cost_reduction_pct"
    ],
    errors="ignore",
)


final_scenarios = cost_long.merge(
    operational_for_merge,
    on="cycle_reduction_sec",
    how="left",
    validate="many_to_one",
)


# -----------------------------------------------------------------------------
# Evidence labels
# -----------------------------------------------------------------------------

final_scenarios[
    "production_evidence_class"
] = "OBSERVED / PROJECT-DERIVED"

final_scenarios[
    "cycle_reduction_class"
] = "SCENARIO ASSUMPTION"

final_scenarios[
    "labor_allocation_class"
] = "SCENARIO ASSUMPTION"

final_scenarios[
    "benchmark_cost_class"
] = "BENCHMARK SCENARIO OUTPUT"


# =============================================================================
# 10. BUILD EVIDENCE REGISTER
# =============================================================================

evidence_rows = [
    {
        "analytical_element":
            "Production event timestamps",

        "evidence_class":
            "OBSERVED",

        "source":
            "NIST PartData",

        "use":
            "Production-flow and stage timing reconstruction",

        "limitation":
            "Source timestamps required documented normalization",
    },
    {
        "analytical_element":
            "UR3 PLC telemetry",

        "evidence_class":
            "OBSERVED",

        "source":
            "NIST UR3Data",

        "use":
            "Dual-robot motion analysis",

        "limitation":
            "Robot role not explicitly labelled in source data",
    },
    {
        "analytical_element":
            "UR5 PLC telemetry",

        "evidence_class":
            "OBSERVED",

        "source":
            "NIST UR5Data",

        "use":
            "Dual-robot motion analysis",

        "limitation":
            "Robot role not explicitly labelled in source data",
    },
    {
        "analytical_element":
            "UR5 RTDE telemetry",

        "evidence_class":
            "OBSERVED",

        "source":
            "NIST UR5RTDE",

        "use":
            "High-frequency diagnostic context",

        "limitation":
            (
                "Diagnostic layer; not used as the common "
                "dual-robot production timeline"
            ),
    },
    {
        "analytical_element":
            "44.318-second production heartbeat",

        "evidence_class":
            "PROJECT-DERIVED",

        "source":
            "Steady-state PartRemoved cadence",

        "use":
            "Baseline production rate",

        "limitation":
            "Represents the analysed experimental run",
    },
    {
        "analytical_element":
            "Capacity-setting task process",

        "evidence_class":
            "PROJECT-DERIVED",

        "source":
            "t6-to-t9 task-process validation",

        "use":
            "Identify the process synchronized with production cadence",

        "limitation":
            (
                "Described as capacity-setting process rather than "
                "assigning causal bottleneck ownership to one robot"
            ),
    },
    {
        "analytical_element":
            "1-5 second cycle reductions",

        "evidence_class":
            "SCENARIO ASSUMPTION",

        "source":
            "Analytical scenario",

        "use":
            "Throughput and time-recovery sensitivity analysis",

        "limitation":
            (
                "Assumes cycle reduction translates into production "
                "heartbeat reduction while no new constraint becomes active"
            ),
    },
    {
        "analytical_element":
            "BLS manufacturing compensation",

        "evidence_class":
            "PUBLIC BENCHMARK",

        "source":
            "U.S. Bureau of Labor Statistics",

        "use":
            "Illustrative labor-cost scenario",

        "limitation":
            "Not observed NIST staffing cost",
    },
    {
        "analytical_element":
            "EIA industrial electricity price",

        "evidence_class":
            "PUBLIC BENCHMARK",

        "source":
            "U.S. Energy Information Administration",

        "use":
            "Illustrative electricity-cost scenario",

        "limitation":
            "Not the measured NIST facility electricity tariff",
    },
    {
        "analytical_element":
            "UR3e / UR5e power",

        "evidence_class":
            "PUBLIC MANUFACTURER PROXY",

        "source":
            "Universal Robots",

        "use":
            "Robot electrical-energy proxy",

        "limitation":
            (
                "e-Series published values are proxies rather than "
                "measured power from the experimental robots"
            ),
    },
    {
        "analytical_element":
            "Benchmark cost per part",

        "evidence_class":
            "BENCHMARK SCENARIO OUTPUT",

        "source":
            "Observed throughput + public benchmarks + assumptions",

        "use":
            "Illustrate time-dependent economic sensitivity",

        "limitation":
            "Not actual NIST accounting cost per part",
    },
]


final_evidence = pd.DataFrame(
    evidence_rows
)


# =============================================================================
# 11. SAVE FINAL ANALYTICAL LAYER
# =============================================================================

final_kpis.to_csv(
    FINAL_KPI_FILE,
    index=False,
)

final_scenarios.to_csv(
    FINAL_SCENARIO_FILE,
    index=False,
)

final_evidence.to_csv(
    FINAL_EVIDENCE_FILE,
    index=False,
)


# =============================================================================
# 12. DISPLAY FINAL KPI REGISTER
# =============================================================================

print("\n" + "=" * 90)
print("FINAL OPERATIONAL KPI REGISTER")
print("=" * 90)

print(
    final_kpis[
        [
            "kpi_name",
            "value",
            "unit",
            "evidence_class",
        ]
    ]
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 13. DISPLAY OPERATIONAL SCENARIO SUMMARY
# =============================================================================

print("\n" + "=" * 90)
print("FINAL OPERATIONAL SCENARIO SUMMARY")
print("=" * 90)

scenario_display_columns = [
    "cycle_reduction_sec",
    "scenario_cycle_sec",
    "scenario_parts_per_hour",
    "throughput_gain_pct",
    "time_recovered_min_per_1000_parts",
    "additional_parts_8h",
    "additional_parts_12h",
    "additional_parts_24h",
    "relative_time_cost_reduction_pct",
]

existing_display_columns = [
    col
    for col in scenario_display_columns
    if col in scenario.columns
]

print(
    scenario[
        existing_display_columns
    ]
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 14. DISPLAY 1.0-FTE BENCHMARK ECONOMIC VIEW
# =============================================================================

print("\n" + "=" * 90)
print("1.0-FTE PUBLIC-BENCHMARK ECONOMIC VIEW")
print("=" * 90)

fte_one = final_scenarios[
    np.isclose(
        final_scenarios[
            "labor_fte_assumption"
        ],
        1.0,
    )
].copy()

fte_display_columns = [
    "cycle_reduction_sec",
    "scenario_parts_per_hour",
    "throughput_gain_pct",
    "benchmark_time_cost_per_part_usd",
    "relative_time_cost_reduction_pct",
]

print(
    fte_one[
        fte_display_columns
    ]
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 15. DISPLAY EVIDENCE REGISTER
# =============================================================================

print("\n" + "=" * 90)
print("FINAL EVIDENCE REGISTER")
print("=" * 90)

print(
    final_evidence[
        [
            "analytical_element",
            "evidence_class",
            "source",
        ]
    ]
    .to_string(index=False)
)


# =============================================================================
# 16. OUTPUT SUMMARY
# =============================================================================

print("\n" + "=" * 90)
print("OUTPUTS")
print("=" * 90)

print(
    f"\n1. KPI register:\n"
    f"   {FINAL_KPI_FILE}"
)

print(
    f"   Shape: "
    f"{final_kpis.shape}"
)

print(
    f"\n2. Throughput + cost scenarios:\n"
    f"   {FINAL_SCENARIO_FILE}"
)

print(
    f"   Shape: "
    f"{final_scenarios.shape}"
)

print(
    f"\n3. Evidence register:\n"
    f"   {FINAL_EVIDENCE_FILE}"
)

print(
    f"   Shape: "
    f"{final_evidence.shape}"
)


# =============================================================================
# 17. FINAL ANALYTICAL STATEMENT
# =============================================================================

print("\n" + "=" * 90)
print("FINAL ANALYTICAL STATEMENT")
print("=" * 90)

print(
    f"""
The analysed NIST robotic work cell exhibits a stable steady-state
production heartbeat of approximately {baseline_cycle_sec:.2f} seconds
per completed part, equivalent to approximately
{baseline_throughput_pph:.2f} parts per hour.

The t6-to-t9 task process is tightly synchronized with this production
cadence and is therefore treated as the leading capacity-setting
process in the analysed baseline.

This does NOT establish that one individual robot is independently
responsible for the production constraint. The cell is pipelined and
both robots operate concurrently across different parts.

Dual-robot motion signatures provide strong empirical support for UR5
performing material-handling activity, while UR3 task/drawing ownership
is supported by task-boundary motion. These role interpretations remain
empirical rather than directly labelled in the source dataset.

Cycle-time reductions of 1 to 5 seconds are scenario assumptions rather
than observed improvements. Their throughput, capacity-recovery and
economic effects are therefore scenario outputs.

The economic analysis measures the sensitivity of the time-dependent
cost component per part. Public BLS and EIA benchmarks and Universal
Robots power proxies provide transparent external assumptions.

The resulting benchmark dollar values are not the actual accounting
cost of the NIST robotic work cell.
"""
)