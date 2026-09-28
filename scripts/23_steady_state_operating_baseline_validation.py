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

DEVIATION_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pca_within_stage_deviation.csv"
)

PARTDATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "partdata_normalized.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "steady_state_operating_baseline_validation.csv"
)

CYCLE_OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "steady_state_cycle_behaviour_validation.csv"
)


# =============================================================================
# 2. CONFIGURATION
# =============================================================================

STEADY_STATE_START = 6
STEADY_STATE_END = 55

PART_EVENT_DIVISOR = 1e7


# =============================================================================
# 3. LOAD DATA
# =============================================================================

print("=" * 90)
print("NIST ROBOTIC WORK CELL - STEADY-STATE OPERATING BASELINE VALIDATION")
print("=" * 90)


if not DEVIATION_FILE.exists():
    raise FileNotFoundError(
        f"Deviation file not found:\n{DEVIATION_FILE}"
    )

if not PARTDATA_FILE.exists():
    raise FileNotFoundError(
        f"PartData file not found:\n{PARTDATA_FILE}"
    )


deviation = pd.read_csv(DEVIATION_FILE)
partdata = pd.read_csv(PARTDATA_FILE)


print(f"\nDeviation dataset shape: {deviation.shape}")
print(f"PartData shape:          {partdata.shape}")


# =============================================================================
# 4. VALIDATE REQUIRED COLUMNS
# =============================================================================

deviation_required = [
    "cycle_id",
    "work_fixture",
    "stage",
    "stage_duration_sec",
    "within_stage_pca_distance",
    "stage_high_deviation",
    "stage_duration_abs_z",
]

partdata_required = [
    "cycle_id",
    "TaskActionStart",
    "PartRemoved",
]


missing_deviation = [
    col for col in deviation_required
    if col not in deviation.columns
]

missing_partdata = [
    col for col in partdata_required
    if col not in partdata.columns
]


if missing_deviation:
    raise ValueError(
        f"Missing deviation columns:\n{missing_deviation}"
    )

if missing_partdata:
    raise ValueError(
        f"Missing PartData columns:\n{missing_partdata}"
    )


# =============================================================================
# 5. NUMERIC PREPARATION
# =============================================================================

for column in [
    "cycle_id",
    "work_fixture",
    "stage_duration_sec",
    "within_stage_pca_distance",
    "stage_duration_abs_z",
]:

    deviation[column] = pd.to_numeric(
        deviation[column],
        errors="coerce",
    )


# CSV boolean columns can occasionally return as strings.
if deviation["stage_high_deviation"].dtype != bool:

    deviation["stage_high_deviation"] = (
        deviation["stage_high_deviation"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
            }
        )
    )


for column in [
    "cycle_id",
    "TaskActionStart",
    "PartRemoved",
]:

    partdata[column] = pd.to_numeric(
        partdata[column],
        errors="coerce",
    )


# =============================================================================
# 6. ISOLATE STEADY-STATE PRODUCTION
# =============================================================================

steady = (
    deviation[
        deviation["cycle_id"].between(
            STEADY_STATE_START,
            STEADY_STATE_END,
        )
    ]
    .copy()
)


print("\n" + "=" * 90)
print("STEADY-STATE ANALYTICAL POPULATION")
print("=" * 90)


print(f"\nCycles: {STEADY_STATE_START}-{STEADY_STATE_END}")
print(f"Cycles represented: {steady['cycle_id'].nunique()}")
print(f"Stage observations: {len(steady)}")
print(f"Stages represented: {steady['stage'].nunique()}")


high_count = int(
    steady["stage_high_deviation"].sum()
)


print(f"High-deviation stage observations: {high_count}")

print(
    f"High-deviation rate: "
    f"{steady['stage_high_deviation'].mean() * 100:.2f}%"
)


# =============================================================================
# 7. STEADY-STATE DEVIATION BY PROCESS STAGE
# =============================================================================

stage_summary = (
    steady
    .groupby(
        "stage",
        as_index=False,
        sort=False,
    )
    .agg(
        observations=(
            "cycle_id",
            "size",
        ),

        mean_pca_distance=(
            "within_stage_pca_distance",
            "mean",
        ),

        median_pca_distance=(
            "within_stage_pca_distance",
            "median",
        ),

        max_pca_distance=(
            "within_stage_pca_distance",
            "max",
        ),

        high_deviation_count=(
            "stage_high_deviation",
            "sum",
        ),

        mean_abs_duration_z=(
            "stage_duration_abs_z",
            "mean",
        ),
    )
)


stage_summary["high_deviation_pct"] = (
    stage_summary["high_deviation_count"]
    / stage_summary["observations"]
    * 100
)


print("\n" + "=" * 90)
print("STEADY-STATE DEVIATION BY PROCESS STAGE")
print("=" * 90)


print(
    stage_summary
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 8. BUILD PRODUCTION HEARTBEATS
# =============================================================================

# PartData event timestamps are on the validated /1e7 event-time scale.
#
# Heartbeats are calculated between consecutive production cycles:
#
#     current TaskActionStart -> next TaskActionStart
#
# and
#
#     current PartRemoved -> next PartRemoved
#
# We restrict transitions to:
#
#     current cycles 6-54
#     next cycles    7-55
#
# so that both sides of every heartbeat remain inside steady state.


parts = (
    partdata[
        partdata["cycle_id"].between(
            STEADY_STATE_START,
            STEADY_STATE_END,
        )
    ][
        [
            "cycle_id",
            "TaskActionStart",
            "PartRemoved",
        ]
    ]
    .sort_values("cycle_id")
    .copy()
)


parts["task_start_sec"] = (
    parts["TaskActionStart"]
    / PART_EVENT_DIVISOR
)

parts["part_removed_sec"] = (
    parts["PartRemoved"]
    / PART_EVENT_DIVISOR
)


parts["next_cycle_id"] = (
    parts["cycle_id"]
    .shift(-1)
)


parts["next_task_start_sec"] = (
    parts["task_start_sec"]
    .shift(-1)
)


parts["next_part_removed_sec"] = (
    parts["part_removed_sec"]
    .shift(-1)
)


parts["task_start_heartbeat_sec"] = (
    parts["next_task_start_sec"]
    - parts["task_start_sec"]
)


parts["part_removed_heartbeat_sec"] = (
    parts["next_part_removed_sec"]
    - parts["part_removed_sec"]
)


heartbeat = (
    parts[
        parts["next_cycle_id"].notna()
    ][
        [
            "cycle_id",
            "next_cycle_id",
            "task_start_heartbeat_sec",
            "part_removed_heartbeat_sec",
        ]
    ]
    .copy()
)


print("\n" + "=" * 90)
print("STEADY-STATE PRODUCTION HEARTBEAT")
print("=" * 90)


heartbeat_summary = (
    heartbeat[
        [
            "task_start_heartbeat_sec",
            "part_removed_heartbeat_sec",
        ]
    ]
    .agg(
        [
            "count",
            "mean",
            "std",
            "min",
            "median",
            "max",
        ]
    )
)


print(
    heartbeat_summary
    .round(4)
    .to_string()
)


# =============================================================================
# 9. CYCLE-LEVEL PCA BEHAVIOUR
# =============================================================================

cycle_behaviour = (
    steady
    .groupby(
        "cycle_id",
        as_index=False,
    )
    .agg(
        stages_observed=(
            "stage",
            "size",
        ),

        mean_pca_distance=(
            "within_stage_pca_distance",
            "mean",
        ),

        max_pca_distance=(
            "within_stage_pca_distance",
            "max",
        ),

        high_deviation_stages=(
            "stage_high_deviation",
            "sum",
        ),

        mean_abs_stage_duration_z=(
            "stage_duration_abs_z",
            "mean",
        ),

        max_abs_stage_duration_z=(
            "stage_duration_abs_z",
            "max",
        ),
    )
)


cycle_behaviour["has_high_deviation"] = (
    cycle_behaviour["high_deviation_stages"] > 0
)


# =============================================================================
# 10. MERGE CYCLE BEHAVIOUR WITH NEXT-CYCLE HEARTBEAT
# =============================================================================

# The PCA behaviour belongs to the CURRENT cycle.
#
# The heartbeat measures the time from the current production event to the
# corresponding event in the NEXT cycle.
#
# This lets us ask whether a cycle containing unusual robot behaviour is
# followed by a materially different production cadence.


cycle_validation = (
    heartbeat
    .merge(
        cycle_behaviour,
        on="cycle_id",
        how="left",
        validate="one_to_one",
    )
)


print("\n" + "=" * 90)
print("CYCLE-LEVEL VALIDATION DATASET")
print("=" * 90)


print(f"\nTransitions represented: {len(cycle_validation)}")

print(
    f"Transitions with complete cycle behaviour: "
    f"{cycle_validation['mean_pca_distance'].notna().sum()}"
)


# =============================================================================
# 11. PCA DEVIATION VS PRODUCTION HEARTBEAT
# =============================================================================

relationship_rows = []


behaviour_metrics = [
    "mean_pca_distance",
    "max_pca_distance",
    "high_deviation_stages",
    "mean_abs_stage_duration_z",
    "max_abs_stage_duration_z",
]


heartbeat_metrics = [
    "task_start_heartbeat_sec",
    "part_removed_heartbeat_sec",
]


for behaviour_metric in behaviour_metrics:

    for heartbeat_metric in heartbeat_metrics:

        valid = (
            cycle_validation[
                [
                    behaviour_metric,
                    heartbeat_metric,
                ]
            ]
            .dropna()
        )


        correlation = (
            valid[behaviour_metric]
            .corr(
                valid[heartbeat_metric]
            )
        )


        relationship_rows.append(
            {
                "behaviour_metric":
                    behaviour_metric,

                "heartbeat_metric":
                    heartbeat_metric,

                "observations":
                    len(valid),

                "correlation":
                    correlation,

                "abs_correlation":
                    abs(correlation)
                    if pd.notna(correlation)
                    else np.nan,
            }
        )


relationship_df = (
    pd.DataFrame(
        relationship_rows
    )
    .sort_values(
        "abs_correlation",
        ascending=False,
    )
)


print("\n" + "=" * 90)
print("PCA BEHAVIOUR VS PRODUCTION HEARTBEAT")
print("=" * 90)


print(
    relationship_df
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 12. HIGH-DEVIATION CYCLES VS OTHER STEADY-STATE CYCLES
# =============================================================================

comparison = (
    cycle_validation
    .groupby(
        "has_high_deviation",
        as_index=False,
    )
    .agg(
        transitions=(
            "cycle_id",
            "size",
        ),

        mean_task_start_heartbeat_sec=(
            "task_start_heartbeat_sec",
            "mean",
        ),

        std_task_start_heartbeat_sec=(
            "task_start_heartbeat_sec",
            "std",
        ),

        mean_part_removed_heartbeat_sec=(
            "part_removed_heartbeat_sec",
            "mean",
        ),

        std_part_removed_heartbeat_sec=(
            "part_removed_heartbeat_sec",
            "std",
        ),

        mean_pca_distance=(
            "mean_pca_distance",
            "mean",
        ),

        mean_max_pca_distance=(
            "max_pca_distance",
            "mean",
        ),
    )
)


print("\n" + "=" * 90)
print("HIGH-DEVIATION CYCLES VS OTHER STEADY-STATE CYCLES")
print("=" * 90)


print(
    comparison
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 13. HEARTBEAT DEVIATION FROM STEADY-STATE BASELINE
# =============================================================================

task_baseline = (
    cycle_validation[
        "task_start_heartbeat_sec"
    ]
    .mean()
)


output_baseline = (
    cycle_validation[
        "part_removed_heartbeat_sec"
    ]
    .mean()
)


cycle_validation[
    "task_start_heartbeat_deviation_sec"
] = (
    cycle_validation[
        "task_start_heartbeat_sec"
    ]
    - task_baseline
)


cycle_validation[
    "part_removed_heartbeat_deviation_sec"
] = (
    cycle_validation[
        "part_removed_heartbeat_sec"
    ]
    - output_baseline
)


cycle_validation[
    "task_start_heartbeat_abs_deviation_sec"
] = (
    cycle_validation[
        "task_start_heartbeat_deviation_sec"
    ]
    .abs()
)


cycle_validation[
    "part_removed_heartbeat_abs_deviation_sec"
] = (
    cycle_validation[
        "part_removed_heartbeat_deviation_sec"
    ]
    .abs()
)


# =============================================================================
# 14. PCA DISTANCE VS ABSOLUTE HEARTBEAT DEVIATION
# =============================================================================

absolute_relationship_rows = []


for behaviour_metric in [
    "mean_pca_distance",
    "max_pca_distance",
    "high_deviation_stages",
]:

    for heartbeat_metric in [
        "task_start_heartbeat_abs_deviation_sec",
        "part_removed_heartbeat_abs_deviation_sec",
    ]:

        valid = (
            cycle_validation[
                [
                    behaviour_metric,
                    heartbeat_metric,
                ]
            ]
            .dropna()
        )


        correlation = (
            valid[behaviour_metric]
            .corr(
                valid[heartbeat_metric]
            )
        )


        absolute_relationship_rows.append(
            {
                "behaviour_metric":
                    behaviour_metric,

                "heartbeat_deviation_metric":
                    heartbeat_metric,

                "observations":
                    len(valid),

                "correlation":
                    correlation,

                "abs_correlation":
                    abs(correlation)
                    if pd.notna(correlation)
                    else np.nan,
            }
        )


absolute_relationship_df = (
    pd.DataFrame(
        absolute_relationship_rows
    )
    .sort_values(
        "abs_correlation",
        ascending=False,
    )
)


print("\n" + "=" * 90)
print("PCA BEHAVIOUR VS ABSOLUTE HEARTBEAT DEVIATION")
print("=" * 90)


print(
    absolute_relationship_df
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 15. MOST DEVIANT STEADY-STATE CYCLES
# =============================================================================

print("\n" + "=" * 90)
print("MOST DEVIANT STEADY-STATE CYCLES")
print("=" * 90)


display_columns = [
    "cycle_id",
    "next_cycle_id",
    "high_deviation_stages",
    "mean_pca_distance",
    "max_pca_distance",
    "task_start_heartbeat_sec",
    "task_start_heartbeat_abs_deviation_sec",
    "part_removed_heartbeat_sec",
    "part_removed_heartbeat_abs_deviation_sec",
]


top_cycles = (
    cycle_validation
    .sort_values(
        [
            "high_deviation_stages",
            "max_pca_distance",
        ],
        ascending=[
            False,
            False,
        ],
    )
    [display_columns]
    .head(20)
)


print(
    top_cycles
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 16. FIXTURE CHECK
# =============================================================================

# Earlier work showed a deterministic alternating fixture structure.
# We therefore inspect whether remaining steady-state deviation flags are
# disproportionately associated with one fixture.


fixture_summary = (
    steady
    .groupby(
        "work_fixture",
        as_index=False,
    )
    .agg(
        observations=(
            "cycle_id",
            "size",
        ),

        mean_pca_distance=(
            "within_stage_pca_distance",
            "mean",
        ),

        high_deviation_count=(
            "stage_high_deviation",
            "sum",
        ),
    )
)


fixture_summary["high_deviation_pct"] = (
    fixture_summary["high_deviation_count"]
    / fixture_summary["observations"]
    * 100
)


print("\n" + "=" * 90)
print("STEADY-STATE DEVIATION BY WORK FIXTURE")
print("=" * 90)


print(
    fixture_summary
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 17. SAVE OUTPUTS
# =============================================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


relationship_output = pd.concat(
    [
        relationship_df.assign(
            relationship_type="signed_heartbeat"
        ),

        absolute_relationship_df.rename(
            columns={
                "heartbeat_deviation_metric":
                    "heartbeat_metric"
            }
        ).assign(
            relationship_type="absolute_heartbeat_deviation"
        ),
    ],
    ignore_index=True,
)


relationship_output.to_csv(
    OUTPUT_FILE,
    index=False,
)


cycle_validation.to_csv(
    CYCLE_OUTPUT_FILE,
    index=False,
)


print("\n" + "=" * 90)
print("OUTPUTS")
print("=" * 90)


print(
    f"\nSteady-state relationship summary:\n"
    f"{OUTPUT_FILE}"
)

print(
    f"\nCycle-level validation dataset:\n"
    f"{CYCLE_OUTPUT_FILE}"
)

print(
    f"\nRelationship output shape: "
    f"{relationship_output.shape}"
)

print(
    f"Cycle validation shape: "
    f"{cycle_validation.shape}"
)


# =============================================================================
# 18. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 90)
print("ANALYTICAL NOTE")
print("=" * 90)


print(
    """
This analysis isolates the central steady-state production region, cycles
6 through 55, because the preceding PCA operating-behaviour analysis showed
that multivariate deviations were strongly concentrated during startup and
runout.

The purpose is to determine whether the smaller number of robot-behaviour
deviations remaining during steady-state production correspond with meaningful
changes in the production heartbeat.

The production heartbeat is evaluated using two independently defined process
cadences:

    TaskActionStart -> next TaskActionStart

and

    PartRemoved -> next PartRemoved.

Only transitions fully contained within cycles 6-55 are used.

The PCA deviation measures are descriptive operating-behaviour indicators.
The 95th-percentile stage flags are not failure labels.

Correlations in this analysis describe association only. They do not establish
that unusual robot motion causes heartbeat variation.

A weak relationship between steady-state PCA deviation and production heartbeat
would support the interpretation that the observed throughput constraint is
primarily a stable, repeating process architecture rather than intermittent
multivariate robot anomalies.

A stronger relationship would justify deeper investigation of the specific
steady-state cycles and stages involved.

No Isolation Forest or additional anomaly model is fitted here. Additional
machine-learning complexity should only be introduced if these results reveal
an unresolved operational question that the current stage-aware PCA analysis
cannot answer.

MLflow remains unnecessary unless multiple legitimate modelling experiments
subsequently need systematic tracking and comparison.
"""
)