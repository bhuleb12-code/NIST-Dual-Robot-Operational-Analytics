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

PART_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "partdata_normalized.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "steady_state_throughput_analysis.csv"
)


# =============================================================================
# 2. CONSTANTS
# =============================================================================

# PartData process-event timestamp differences use /1e7.
EVENT_DIVISOR = 1e7


# =============================================================================
# 3. LOAD DATA
# =============================================================================

part = pd.read_csv(PART_FILE)

part = (
    part
    .sort_values("Part Number")
    .reset_index(drop=True)
)

print("=" * 80)
print("NIST ROBOTIC WORK CELL - STEADY-STATE THROUGHPUT ANALYSIS")
print("=" * 80)

print(f"\nParts: {len(part):,}")

print(
    f"Part Number range: "
    f"{part['Part Number'].min()} -> "
    f"{part['Part Number'].max()}"
)


# =============================================================================
# 4. PROCESS EVENT TIMES
# =============================================================================

event_columns = [
    "PartAdded",
    "PickFromInputAssigned",
    "InputPartPicked",
    "InputPartPlaced",
    "PlaceInWFComplete",
    "TaskAssigned",
    "TaskActionStart",
    "TaskActionComplete",
    "TaskComplete",
    "PickFromWFAssigned",
    "OutputPartPicked",
    "PutputPartPlaced",
    "PlaceInOutputComplete",
    "PartRemoved",
]

for column in event_columns:

    part[f"{column}_sec"] = (
        part[column]
        / EVENT_DIVISOR
    )


# =============================================================================
# 5. WITHIN-PART STAGE DURATIONS
# =============================================================================

part["input_wait_sec"] = (
    part["PickFromInputAssigned_sec"]
    - part["PartAdded_sec"]
)

part["input_handling_sec"] = (
    part["PlaceInWFComplete_sec"]
    - part["PickFromInputAssigned_sec"]
)

part["pre_task_wait_sec"] = (
    part["TaskAssigned_sec"]
    - part["PlaceInWFComplete_sec"]
)

part["task_setup_sec"] = (
    part["TaskActionStart_sec"]
    - part["TaskAssigned_sec"]
)

part["task_action_sec"] = (
    part["TaskActionComplete_sec"]
    - part["TaskActionStart_sec"]
)

part["task_close_sec"] = (
    part["TaskComplete_sec"]
    - part["TaskActionComplete_sec"]
)

part["output_handling_sec"] = (
    part["PlaceInOutputComplete_sec"]
    - part["PickFromWFAssigned_sec"]
)

part["post_output_wait_sec"] = (
    part["PartRemoved_sec"]
    - part["PlaceInOutputComplete_sec"]
)

part["total_flow_sec"] = (
    part["PartRemoved_sec"]
    - part["PartAdded_sec"]
)


# =============================================================================
# 6. INTER-PART CADENCE
# =============================================================================

# For a pipelined cell, throughput should not be inferred from total
# per-part flow time. Instead we examine spacing between consecutive parts
# at multiple process milestones.

cadence_events = {
    "part_added_interval_sec":
        "PartAdded_sec",

    "input_assigned_interval_sec":
        "PickFromInputAssigned_sec",

    "fixture_complete_interval_sec":
        "PlaceInWFComplete_sec",

    "task_start_interval_sec":
        "TaskActionStart_sec",

    "task_complete_interval_sec":
        "TaskActionComplete_sec",

    "output_complete_interval_sec":
        "PlaceInOutputComplete_sec",

    "part_removed_interval_sec":
        "PartRemoved_sec",
}

for output_column, source_column in cadence_events.items():

    part[output_column] = (
        part[source_column]
        .diff()
    )


# =============================================================================
# 7. BASIC CADENCE SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("INTER-PART CADENCE - ALL AVAILABLE INTERVALS")
print("=" * 80)

cadence_summary_rows = []

for cadence_column in cadence_events:

    values = (
        part[cadence_column]
        .dropna()
    )

    cadence_summary_rows.append({
        "milestone":
            cadence_column,

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

        "parts_per_hour_from_mean":
            3600 / values.mean(),
    })

cadence_summary = pd.DataFrame(
    cadence_summary_rows
)

print(
    cadence_summary
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 8. INSPECT INTERVALS BY PART NUMBER
# =============================================================================

print("\n" + "=" * 80)
print("PART-BY-PART CADENCE")
print("=" * 80)

print(
    part[
        [
            "Part Number",
            "Work Fixture",
            "part_added_interval_sec",
            "task_start_interval_sec",
            "task_complete_interval_sec",
            "part_removed_interval_sec",
        ]
    ]
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 9. DETECT STARTUP STABILIZATION
# =============================================================================

# We do not arbitrarily remove the first N parts.
#
# Instead, examine rolling behaviour in the inter-part PartAdded interval.
# A five-interval rolling window is used only as a diagnostic to show where
# the production cadence becomes comparatively stable.

part["arrival_rolling_mean_5"] = (
    part["part_added_interval_sec"]
    .rolling(
        window=5,
        min_periods=5,
    )
    .mean()
)

part["arrival_rolling_sd_5"] = (
    part["part_added_interval_sec"]
    .rolling(
        window=5,
        min_periods=5,
    )
    .std()
)

print("\n" + "=" * 80)
print("ROLLING ARRIVAL-CADENCE DIAGNOSTIC")
print("=" * 80)

print(
    part[
        [
            "Part Number",
            "part_added_interval_sec",
            "arrival_rolling_mean_5",
            "arrival_rolling_sd_5",
        ]
    ]
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 10. CENTRAL PRODUCTION WINDOW
# =============================================================================

# This is intentionally labelled a CENTRAL production window rather than
# automatically declaring it "steady state".
#
# Parts 6-55 exclude the first and last five parts so that startup and
# run-out behaviour can be compared with the central body of production.
#
# Whether this central window is genuinely steady must be supported by
# the results rather than assumed.

CENTRAL_START = 6
CENTRAL_END = 55

central = part[
    part["Part Number"].between(
        CENTRAL_START,
        CENTRAL_END,
    )
].copy()

startup = part[
    part["Part Number"] < CENTRAL_START
].copy()

runout = part[
    part["Part Number"] > CENTRAL_END
].copy()


print("\n" + "=" * 80)
print("ANALYTICAL WINDOWS")
print("=" * 80)

print(
    f"\nStartup window: "
    f"Parts 1-{CENTRAL_START - 1}"
)

print(
    f"Central window: "
    f"Parts {CENTRAL_START}-{CENTRAL_END}"
)

print(
    f"Run-out window: "
    f"Parts {CENTRAL_END + 1}-60"
)

print(
    "\nNOTE: These windows are diagnostic partitions. "
    "They do not by themselves establish steady state."
)


# =============================================================================
# 11. CENTRAL-WINDOW CADENCE
# =============================================================================

print("\n" + "=" * 80)
print("CENTRAL-WINDOW CADENCE")
print("=" * 80)

central_summary_rows = []

for cadence_column in cadence_events:

    values = (
        central[cadence_column]
        .dropna()
    )

    central_summary_rows.append({
        "milestone":
            cadence_column,

        "n":
            len(values),

        "mean_sec":
            values.mean(),

        "median_sec":
            values.median(),

        "sd_sec":
            values.std(),

        "cv_pct":
            (
                values.std()
                / values.mean()
                * 100
            ),

        "parts_per_hour":
            3600 / values.mean(),
    })

central_summary = pd.DataFrame(
    central_summary_rows
)

print(
    central_summary
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 12. STARTUP vs CENTRAL vs RUN-OUT
# =============================================================================

print("\n" + "=" * 80)
print("STARTUP vs CENTRAL vs RUN-OUT")
print("=" * 80)

comparison_rows = []

windows = {
    "startup": startup,
    "central": central,
    "runout": runout,
}

comparison_metrics = [
    "input_wait_sec",
    "pre_task_wait_sec",
    "task_action_sec",
    "total_flow_sec",
]

for window_name, window_df in windows.items():

    for metric in comparison_metrics:

        values = (
            window_df[metric]
            .dropna()
        )

        comparison_rows.append({
            "window":
                window_name,

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
# 13. FIXTURE-SPECIFIC TASK ACTION
# =============================================================================

print("\n" + "=" * 80)
print("TASK ACTION BY WORK FIXTURE")
print("=" * 80)

fixture_task = (
    central
    .groupby(
        "Work Fixture"
    )
    .agg(
        parts=(
            "Part Number",
            "count"
        ),

        mean_task_action_sec=(
            "task_action_sec",
            "mean"
        ),

        median_task_action_sec=(
            "task_action_sec",
            "median"
        ),

        sd_task_action_sec=(
            "task_action_sec",
            "std"
        ),

        min_task_action_sec=(
            "task_action_sec",
            "min"
        ),

        max_task_action_sec=(
            "task_action_sec",
            "max"
        ),
    )
    .reset_index()
)

print(
    fixture_task
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 14. TASK ACTION vs PRODUCTION CADENCE
# =============================================================================

print("\n" + "=" * 80)
print("TASK ACTION vs PRODUCTION CADENCE")
print("=" * 80)

task_action_mean = (
    central["task_action_sec"]
    .mean()
)

arrival_interval_mean = (
    central[
        "part_added_interval_sec"
    ]
    .dropna()
    .mean()
)

completion_interval_mean = (
    central[
        "part_removed_interval_sec"
    ]
    .dropna()
    .mean()
)

print(
    f"\nMean task-action duration: "
    f"{task_action_mean:.4f} sec"
)

print(
    f"Mean PartAdded interval:  "
    f"{arrival_interval_mean:.4f} sec"
)

print(
    f"Mean PartRemoved interval:"
    f" {completion_interval_mean:.4f} sec"
)

print(
    f"\nArrival cadence minus task action: "
    f"{arrival_interval_mean - task_action_mean:.4f} sec"
)

print(
    f"Completion cadence minus task action: "
    f"{completion_interval_mean - task_action_mean:.4f} sec"
)


# =============================================================================
# 15. IMPLIED CAPACITY
# =============================================================================

print("\n" + "=" * 80)
print("OBSERVED CENTRAL-WINDOW THROUGHPUT")
print("=" * 80)

arrival_pph = (
    3600
    / arrival_interval_mean
)

completion_pph = (
    3600
    / completion_interval_mean
)

task_only_pph = (
    3600
    / task_action_mean
)

print(
    f"\nObserved input cadence: "
    f"{arrival_pph:.2f} parts/hour"
)

print(
    f"Observed output cadence: "
    f"{completion_pph:.2f} parts/hour"
)

print(
    f"Task-action-only theoretical rate: "
    f"{task_only_pph:.2f} task actions/hour"
)

print(
    """
The task-action-only rate is NOT a production throughput estimate.
It simply expresses the reciprocal of mean task-action duration.
The cell contains handling, synchronization and overlapping operations,
so it cannot be interpreted as achievable parts/hour by itself.
"""
)


# =============================================================================
# 16. CADENCE DIFFERENCE BY FIXTURE
# =============================================================================

print("=" * 80)
print("INTER-PART CADENCE BY DESTINATION FIXTURE")
print("=" * 80)

fixture_cadence = (
    central
    .dropna(
        subset=[
            "part_added_interval_sec"
        ]
    )
    .groupby(
        "Work Fixture"
    )
    .agg(
        intervals=(
            "part_added_interval_sec",
            "count"
        ),

        mean_arrival_interval_sec=(
            "part_added_interval_sec",
            "mean"
        ),

        median_arrival_interval_sec=(
            "part_added_interval_sec",
            "median"
        ),

        sd_arrival_interval_sec=(
            "part_added_interval_sec",
            "std"
        ),
    )
    .reset_index()
)

print(
    fixture_cadence
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 17. CENTRAL-WINDOW VARIABILITY RANKING
# =============================================================================

print("\n" + "=" * 80)
print("CENTRAL-WINDOW STAGE VARIABILITY")
print("=" * 80)

stage_metrics = [
    "input_wait_sec",
    "input_handling_sec",
    "pre_task_wait_sec",
    "task_setup_sec",
    "task_action_sec",
    "task_close_sec",
    "output_handling_sec",
    "post_output_wait_sec",
]

variability_rows = []

for metric in stage_metrics:

    values = (
        central[metric]
        .dropna()
    )

    variability_rows.append({
        "stage_metric":
            metric,

        "mean_sec":
            values.mean(),

        "sd_sec":
            values.std(),

        "cv_pct":
            (
                values.std()
                / values.mean()
                * 100
            )
            if values.mean() != 0
            else np.nan,

        "min_sec":
            values.min(),

        "max_sec":
            values.max(),
    })

variability = (
    pd.DataFrame(
        variability_rows
    )
    .sort_values(
        "sd_sec",
        ascending=False,
    )
)

print(
    variability
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 18. SAVE
# =============================================================================

output_columns = [
    "cycle_id",
    "Part Number",
    "Work Fixture",
    "input_wait_sec",
    "input_handling_sec",
    "pre_task_wait_sec",
    "task_setup_sec",
    "task_action_sec",
    "task_close_sec",
    "output_handling_sec",
    "post_output_wait_sec",
    "total_flow_sec",
    "part_added_interval_sec",
    "input_assigned_interval_sec",
    "fixture_complete_interval_sec",
    "task_start_interval_sec",
    "task_complete_interval_sec",
    "output_complete_interval_sec",
    "part_removed_interval_sec",
    "arrival_rolling_mean_5",
    "arrival_rolling_sd_5",
]

part[
    output_columns
].to_csv(
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
    f"{part[output_columns].shape}"
)


# =============================================================================
# 19. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
This analysis distinguishes per-part flow time from production cadence.

Because multiple parts are processed concurrently, the approximately
125-second PartAdded-to-PartRemoved flow time must not be interpreted
as the cell cycle time or throughput interval.

Inter-part spacing is evaluated at multiple process milestones.

Parts 6-55 are used as a central diagnostic window to reduce obvious
startup and run-out influence. This partition is not automatically
labelled steady state; the observed results must support that
interpretation.

The approximately 37-second task-action stage may be a candidate
throughput constraint because of its duration and repetition, but
duration alone does not establish a bottleneck. Production cadence,
resource occupancy and synchronization must be considered together.
"""
)