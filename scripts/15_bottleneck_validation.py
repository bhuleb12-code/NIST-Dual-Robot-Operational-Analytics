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

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "partdata_normalized.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bottleneck_validation.csv"
)


# =============================================================================
# 2. CONSTANTS
# =============================================================================

EVENT_DIVISOR = 1e7

CENTRAL_START = 6
CENTRAL_END = 55


# =============================================================================
# 3. LOAD
# =============================================================================

df = pd.read_csv(INPUT_FILE)

df = (
    df
    .sort_values("Part Number")
    .reset_index(drop=True)
)

print("=" * 80)
print("NIST ROBOTIC WORK CELL - BOTTLENECK VALIDATION")
print("=" * 80)

print(f"\nParts: {len(df):,}")
print(
    f"Part Number range: "
    f"{df['Part Number'].min()} -> "
    f"{df['Part Number'].max()}"
)


# =============================================================================
# 4. CONVERT REQUIRED EVENTS TO RELATIVE SECONDS
# =============================================================================

EVENTS = [
    "TaskAssigned",          # t6
    "TaskActionStart",       # t7
    "TaskActionComplete",    # t8
    "TaskComplete",          # t9
    "PartRemoved",           # t14
]

for event in EVENTS:

    df[f"{event}_sec"] = (
        df[event]
        / EVENT_DIVISOR
    )


# =============================================================================
# 5. TASK-PROCESS COMPONENTS
# =============================================================================

df["task_setup_sec"] = (
    df["TaskActionStart_sec"]
    - df["TaskAssigned_sec"]
)

df["task_action_sec"] = (
    df["TaskActionComplete_sec"]
    - df["TaskActionStart_sec"]
)

df["task_close_sec"] = (
    df["TaskComplete_sec"]
    - df["TaskActionComplete_sec"]
)

df["task_process_sec"] = (
    df["TaskComplete_sec"]
    - df["TaskAssigned_sec"]
)


# Check exact decomposition.

df["task_component_sum_sec"] = (
    df["task_setup_sec"]
    + df["task_action_sec"]
    + df["task_close_sec"]
)

df["task_decomposition_error_sec"] = (
    df["task_process_sec"]
    - df["task_component_sum_sec"]
)


# =============================================================================
# 6. PRODUCTION HEARTBEATS
# =============================================================================

# Consecutive task starts.

df["next_part_number"] = (
    df["Part Number"]
    .shift(-1)
)

df["next_work_fixture"] = (
    df["Work Fixture"]
    .shift(-1)
)

df["next_task_start_sec"] = (
    df["TaskActionStart_sec"]
    .shift(-1)
)

df["task_start_heartbeat_sec"] = (
    df["next_task_start_sec"]
    - df["TaskActionStart_sec"]
)


# Consecutive task completions.

df["next_task_complete_sec"] = (
    df["TaskActionComplete_sec"]
    .shift(-1)
)

df["task_action_complete_heartbeat_sec"] = (
    df["next_task_complete_sec"]
    - df["TaskActionComplete_sec"]
)


# Consecutive TaskComplete milestones.

df["next_task_process_complete_sec"] = (
    df["TaskComplete_sec"]
    .shift(-1)
)

df["task_complete_heartbeat_sec"] = (
    df["next_task_process_complete_sec"]
    - df["TaskComplete_sec"]
)


# Consecutive final cell departures.

df["next_part_removed_sec"] = (
    df["PartRemoved_sec"]
    .shift(-1)
)

df["part_removed_heartbeat_sec"] = (
    df["next_part_removed_sec"]
    - df["PartRemoved_sec"]
)


# =============================================================================
# 7. CENTRAL TRANSITIONS
# =============================================================================

# Both the current part and next part must belong to the central window.
# This avoids including the Part 55 -> Part 56 transition.

central = df[
    (df["Part Number"] >= CENTRAL_START)
    & (df["next_part_number"] <= CENTRAL_END)
].copy()

print("\n" + "=" * 80)
print("CENTRAL VALIDATION WINDOW")
print("=" * 80)

print(
    f"\nCurrent Part range: "
    f"{int(central['Part Number'].min())} -> "
    f"{int(central['Part Number'].max())}"
)

print(
    f"Next Part range:    "
    f"{int(central['next_part_number'].min())} -> "
    f"{int(central['next_part_number'].max())}"
)

print(
    f"Transitions:        "
    f"{len(central):,}"
)


# =============================================================================
# 8. TASK-PROCESS DECOMPOSITION
# =============================================================================

print("\n" + "=" * 80)
print("TASK-PROCESS DECOMPOSITION")
print("=" * 80)

task_metrics = [
    "task_setup_sec",
    "task_action_sec",
    "task_close_sec",
    "task_process_sec",
]

task_summary_rows = []

for metric in task_metrics:

    values = (
        central[metric]
        .dropna()
    )

    task_summary_rows.append({
        "metric":
            metric,

        "n":
            len(values),

        "mean_sec":
            values.mean(),

        "median_sec":
            values.median(),

        "sd_sec":
            values.std(),

        "min_sec":
            values.min(),

        "max_sec":
            values.max(),

        "cv_pct":
            (
                values.std()
                / values.mean()
                * 100
            ),
    })


task_summary = pd.DataFrame(
    task_summary_rows
)

print(
    task_summary
    .round(4)
    .to_string(index=False)
)


print(
    "\nMaximum absolute task-decomposition error: "
    f"{central['task_decomposition_error_sec'].abs().max():.10f} sec"
)


# =============================================================================
# 9. HEARTBEAT SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("PRODUCTION HEARTBEAT SUMMARY")
print("=" * 80)

heartbeat_metrics = [
    "task_start_heartbeat_sec",
    "task_action_complete_heartbeat_sec",
    "task_complete_heartbeat_sec",
    "part_removed_heartbeat_sec",
]

heartbeat_rows = []

for metric in heartbeat_metrics:

    values = (
        central[metric]
        .dropna()
    )

    heartbeat_rows.append({
        "metric":
            metric,

        "n":
            len(values),

        "mean_sec":
            values.mean(),

        "median_sec":
            values.median(),

        "sd_sec":
            values.std(),

        "min_sec":
            values.min(),

        "max_sec":
            values.max(),

        "parts_per_hour":
            3600 / values.mean(),
    })


heartbeat_summary = pd.DataFrame(
    heartbeat_rows
)

print(
    heartbeat_summary
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 10. TASK PROCESS vs HEARTBEAT
# =============================================================================

print("\n" + "=" * 80)
print("TASK PROCESS vs PRODUCTION HEARTBEAT")
print("=" * 80)

central[
    "task_process_minus_task_start_heartbeat_sec"
] = (
    central["task_process_sec"]
    - central["task_start_heartbeat_sec"]
)

central[
    "task_process_minus_output_heartbeat_sec"
] = (
    central["task_process_sec"]
    - central["part_removed_heartbeat_sec"]
)


comparison_metrics = [
    "task_process_sec",
    "task_start_heartbeat_sec",
    "part_removed_heartbeat_sec",
    "task_process_minus_task_start_heartbeat_sec",
    "task_process_minus_output_heartbeat_sec",
]

comparison_rows = []

for metric in comparison_metrics:

    values = (
        central[metric]
        .dropna()
    )

    comparison_rows.append({
        "metric":
            metric,

        "mean_sec":
            values.mean(),

        "median_sec":
            values.median(),

        "sd_sec":
            values.std(),

        "min_sec":
            values.min(),

        "max_sec":
            values.max(),
    })


comparison = pd.DataFrame(
    comparison_rows
)

print(
    comparison
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 11. ABSOLUTE DIFFERENCE
# =============================================================================

central[
    "abs_task_process_vs_heartbeat_diff_sec"
] = (
    central[
        "task_process_minus_task_start_heartbeat_sec"
    ]
    .abs()
)

print("\n" + "=" * 80)
print("TASK-PROCESS / HEARTBEAT MATCH")
print("=" * 80)

match = (
    central[
        "abs_task_process_vs_heartbeat_diff_sec"
    ]
    .dropna()
)

print(
    f"\nMean absolute difference:   "
    f"{match.mean():.4f} sec"
)

print(
    f"Median absolute difference: "
    f"{match.median():.4f} sec"
)

print(
    f"Maximum absolute difference:"
    f" {match.max():.4f} sec"
)

print(
    f"\nWithin 0.10 sec: "
    f"{(match <= 0.10).sum()} / {len(match)} "
    f"({(match <= 0.10).mean() * 100:.2f}%)"
)

print(
    f"Within 0.25 sec: "
    f"{(match <= 0.25).sum()} / {len(match)} "
    f"({(match <= 0.25).mean() * 100:.2f}%)"
)

print(
    f"Within 0.50 sec: "
    f"{(match <= 0.50).sum()} / {len(match)} "
    f"({(match <= 0.50).mean() * 100:.2f}%)"
)

print(
    f"Within 1.00 sec: "
    f"{(match <= 1.00).sum()} / {len(match)} "
    f"({(match <= 1.00).mean() * 100:.2f}%)"
)


# =============================================================================
# 12. CORRELATION
# =============================================================================

print("\n" + "=" * 80)
print("CYCLE-BY-CYCLE ASSOCIATION")
print("=" * 80)

valid = central[
    [
        "task_process_sec",
        "task_start_heartbeat_sec",
        "part_removed_heartbeat_sec",
    ]
].dropna()

corr_task = (
    valid[
        "task_process_sec"
    ]
    .corr(
        valid[
            "task_start_heartbeat_sec"
        ]
    )
)

corr_output = (
    valid[
        "task_process_sec"
    ]
    .corr(
        valid[
            "part_removed_heartbeat_sec"
        ]
    )
)

print(
    f"\nCorrelation: task process vs "
    f"TaskStart heartbeat = "
    f"{corr_task:.4f}"
)

print(
    f"Correlation: task process vs "
    f"PartRemoved heartbeat = "
    f"{corr_output:.4f}"
)

print(
    "\nNOTE: Correlation is descriptive. "
    "It is not interpreted as causation."
)


# =============================================================================
# 13. FIXTURE-SPECIFIC VALIDATION
# =============================================================================

print("\n" + "=" * 80)
print("FIXTURE-SPECIFIC VALIDATION")
print("=" * 80)

fixture_summary = (
    central
    .groupby(
        [
            "Work Fixture",
            "next_work_fixture",
        ]
    )
    .agg(
        transitions=(
            "Part Number",
            "count"
        ),

        mean_task_setup_sec=(
            "task_setup_sec",
            "mean"
        ),

        mean_task_action_sec=(
            "task_action_sec",
            "mean"
        ),

        mean_task_close_sec=(
            "task_close_sec",
            "mean"
        ),

        mean_task_process_sec=(
            "task_process_sec",
            "mean"
        ),

        mean_task_start_heartbeat_sec=(
            "task_start_heartbeat_sec",
            "mean"
        ),

        mean_output_heartbeat_sec=(
            "part_removed_heartbeat_sec",
            "mean"
        ),

        mean_task_minus_heartbeat_sec=(
            "task_process_minus_task_start_heartbeat_sec",
            "mean"
        ),

        sd_task_minus_heartbeat_sec=(
            "task_process_minus_task_start_heartbeat_sec",
            "std"
        ),
    )
    .reset_index()
)

print(
    fixture_summary
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 14. PART-BY-PART VALIDATION
# =============================================================================

print("\n" + "=" * 80)
print("PART-BY-PART VALIDATION")
print("=" * 80)

display_columns = [
    "Part Number",
    "Work Fixture",
    "next_part_number",
    "next_work_fixture",
    "task_setup_sec",
    "task_action_sec",
    "task_close_sec",
    "task_process_sec",
    "task_start_heartbeat_sec",
    "part_removed_heartbeat_sec",
    "task_process_minus_task_start_heartbeat_sec",
]

print(
    central[
        display_columns
    ]
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 15. ALTERNATING FIXTURE PATTERN
# =============================================================================

print("\n" + "=" * 80)
print("ALTERNATING FIXTURE PATTERN")
print("=" * 80)

for fixture in sorted(
    central["Work Fixture"]
    .dropna()
    .unique()
):

    subset = central[
        central["Work Fixture"] == fixture
    ]

    print(
        f"\nFixture {int(fixture)}:"
    )

    print(
        f"  Mean task process: "
        f"{subset['task_process_sec'].mean():.4f} sec"
    )

    print(
        f"  Mean next-start heartbeat: "
        f"{subset['task_start_heartbeat_sec'].mean():.4f} sec"
    )

    print(
        f"  Mean difference: "
        f"{subset['task_process_minus_task_start_heartbeat_sec'].mean():.4f} sec"
    )

    print(
        f"  SD difference: "
        f"{subset['task_process_minus_task_start_heartbeat_sec'].std():.4f} sec"
    )


# =============================================================================
# 16. IMPLIED TASK-RESOURCE CAPACITY
# =============================================================================

print("\n" + "=" * 80)
print("IMPLIED TASK-PROCESS CAPACITY")
print("=" * 80)

mean_task_process = (
    central[
        "task_process_sec"
    ]
    .mean()
)

mean_task_heartbeat = (
    central[
        "task_start_heartbeat_sec"
    ]
    .mean()
)

mean_output_heartbeat = (
    central[
        "part_removed_heartbeat_sec"
    ]
    .mean()
)

task_process_rate = (
    3600
    / mean_task_process
)

task_heartbeat_rate = (
    3600
    / mean_task_heartbeat
)

output_rate = (
    3600
    / mean_output_heartbeat
)

print(
    f"\nMean t6->t9 task process: "
    f"{mean_task_process:.4f} sec"
)

print(
    f"Reciprocal task-process rate: "
    f"{task_process_rate:.2f} per hour"
)

print(
    f"\nMean TaskStart heartbeat: "
    f"{mean_task_heartbeat:.4f} sec"
)

print(
    f"Observed task-start rate: "
    f"{task_heartbeat_rate:.2f} per hour"
)

print(
    f"\nMean PartRemoved heartbeat: "
    f"{mean_output_heartbeat:.4f} sec"
)

print(
    f"Observed output rate: "
    f"{output_rate:.2f} parts/hour"
)

print(
    "\nThe reciprocal task-process rate is a timing comparison, "
    "not an independent throughput forecast."
)


# =============================================================================
# 17. SAVE
# =============================================================================

output_columns = [
    "cycle_id",
    "Part Number",
    "Work Fixture",
    "next_part_number",
    "next_work_fixture",
    "task_setup_sec",
    "task_action_sec",
    "task_close_sec",
    "task_process_sec",
    "task_start_heartbeat_sec",
    "task_action_complete_heartbeat_sec",
    "task_complete_heartbeat_sec",
    "part_removed_heartbeat_sec",
    "task_process_minus_task_start_heartbeat_sec",
    "task_process_minus_output_heartbeat_sec",
    "abs_task_process_vs_heartbeat_diff_sec",
]

output = central[
    output_columns
].copy()

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

output.to_csv(
    OUTPUT_FILE,
    index=False,
)

print("\n" + "=" * 80)
print("OUTPUT")
print("=" * 80)

print(
    f"\nSaved:\n{OUTPUT_FILE}"
)

print(
    f"\nOutput shape: "
    f"{output.shape}"
)


# =============================================================================
# 18. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
This script tests whether the complete t6->t9 task-process interval
(TaskAssigned -> TaskComplete) is closely aligned with the recurring
steady-state production heartbeat.

A close numerical match is evidence that the task-process sequence is
operating at approximately the same cadence as the cell's production
rhythm.

However, equality of durations alone does not prove causality or prove
that every second of t6->t9 represents exclusive robot occupancy.

The bottleneck interpretation should therefore combine:

1. repeated steady-state cadence,
2. task-process duration,
3. fixture-specific timing structure,
4. robot-motion evidence, and
5. process-sequence semantics.

Any capacity-improvement scenario should be calculated only after the
throughput constraint has been supported by this combined evidence.
"""
)