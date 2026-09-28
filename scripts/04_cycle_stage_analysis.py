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

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "cycle_stage_durations.csv"


# =============================================================================
# 2. LOAD NORMALIZED PART DATA
# =============================================================================

df = pd.read_csv(INPUT_FILE)

print("=" * 80)
print("NIST ROBOTIC WORK CELL - CYCLE STAGE ANALYSIS")
print("=" * 80)

print(f"\nRows:    {len(df):,}")
print(f"Columns: {df.shape[1]:,}")


# =============================================================================
# 3. NIST EVENT SEQUENCE
# =============================================================================

events = [
    ("t1", "PartAdded"),
    ("t2", "PickFromInputAssigned"),
    ("t3", "InputPartPicked"),
    ("t4", "InputPartPlaced"),
    ("t5", "PlaceInWFComplete"),
    ("t6", "TaskAssigned"),
    ("t7", "TaskActionStart"),
    ("t8", "TaskActionComplete"),
    ("t9", "TaskComplete"),
    ("t10", "PickFromWFAssigned"),
    ("t11", "OutputPartPicked"),
    ("t12", "PutputPartPlaced"),
    ("t13", "PlaceInOutputComplete"),
    ("t14", "PartRemoved"),
]


# =============================================================================
# 4. PLC TIME SCALE
# =============================================================================

# The supplied NIST README contains an incomplete exponent for the PartData
# PLC timestamps. A divisor of 10^7 is used here based on:
#
# 1. The documented 10^7 conversion for PLCTime in UR3Data/UR5Data.
# 2. The resulting physical event durations being consistent with the
#    NIST work-cell process timeline.
# 3. Near-immediate PLC transitions becoming approximately 0.004-0.006 s.
#
# This assumption remains explicitly documented for traceability.

PLC_TIME_DIVISOR = 1e7


# =============================================================================
# 5. CALCULATE ALL 13 EVENT-TO-EVENT DURATIONS
# =============================================================================

transition_labels = {
    "t1_to_t2_sec": "Wait for input-pick assignment",
    "t2_to_t3_sec": "Input pick",
    "t3_to_t4_sec": "Move input part to work fixture",
    "t4_to_t5_sec": "Complete work-fixture placement",
    "t5_to_t6_sec": "Wait for task assignment",
    "t6_to_t7_sec": "Prepare/start task action",
    "t7_to_t8_sec": "Task action",
    "t8_to_t9_sec": "Complete task",
    "t9_to_t10_sec": "Assign work-fixture pick",
    "t10_to_t11_sec": "Pick part from work fixture",
    "t11_to_t12_sec": "Move part to output",
    "t12_to_t13_sec": "Complete output placement",
    "t13_to_t14_sec": "Wait for part removal",
}

transition_columns = []

for i in range(len(events) - 1):

    start_t, start_column = events[i]
    end_t, end_column = events[i + 1]

    new_column = f"{start_t}_to_{end_t}_sec"

    df[new_column] = (
        df[end_column] - df[start_column]
    ) / PLC_TIME_DIVISOR

    transition_columns.append(new_column)


# =============================================================================
# 6. OVERALL PART FLOW TIME
# =============================================================================

df["total_flow_time_sec"] = (
    df["PartRemoved"] - df["PartAdded"]
) / PLC_TIME_DIVISOR


# =============================================================================
# 7. BROAD OPERATIONAL PHASES
# =============================================================================

# These phases preserve the NIST event boundaries rather than assigning
# causality to a robot before the robot/process alignment is analysed.

df["pre_inbound_wait_sec"] = (
    df["PickFromInputAssigned"]
    - df["PartAdded"]
) / PLC_TIME_DIVISOR

df["inbound_handling_sec"] = (
    df["PlaceInWFComplete"]
    - df["PickFromInputAssigned"]
) / PLC_TIME_DIVISOR

df["pre_task_wait_sec"] = (
    df["TaskAssigned"]
    - df["PlaceInWFComplete"]
) / PLC_TIME_DIVISOR

df["task_process_sec"] = (
    df["TaskComplete"]
    - df["TaskAssigned"]
) / PLC_TIME_DIVISOR

df["outbound_handling_sec"] = (
    df["PlaceInOutputComplete"]
    - df["PickFromWFAssigned"]
) / PLC_TIME_DIVISOR

df["post_output_wait_sec"] = (
    df["PartRemoved"]
    - df["PlaceInOutputComplete"]
) / PLC_TIME_DIVISOR


phase_columns = [
    "pre_inbound_wait_sec",
    "inbound_handling_sec",
    "pre_task_wait_sec",
    "task_process_sec",
    "outbound_handling_sec",
    "post_output_wait_sec",
]


# =============================================================================
# 8. VALIDATE TRANSITION DURATIONS
# =============================================================================

print("\n" + "=" * 80)
print("DURATION VALIDATION")
print("=" * 80)

negative_counts = (df[transition_columns] < 0).sum()

print("\nNegative durations by transition:")

for column, count in negative_counts.items():
    print(f"{column:<20} {count:>3}")

print(
    f"\nRows with any negative transition: "
    f"{(df[transition_columns] < 0).any(axis=1).sum():,}"
)


# =============================================================================
# 9. TRANSITION-LEVEL SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("EVENT-TO-EVENT DURATION SUMMARY (SECONDS)")
print("=" * 80)

transition_summary = pd.DataFrame({
    "stage": [
        transition_labels[column]
        for column in transition_columns
    ],
    "mean_sec": [
        df[column].mean()
        for column in transition_columns
    ],
    "median_sec": [
        df[column].median()
        for column in transition_columns
    ],
    "std_sec": [
        df[column].std()
        for column in transition_columns
    ],
    "min_sec": [
        df[column].min()
        for column in transition_columns
    ],
    "max_sec": [
        df[column].max()
        for column in transition_columns
    ],
})

transition_summary["cv"] = (
    transition_summary["std_sec"]
    / transition_summary["mean_sec"]
)

print(
    transition_summary
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 10. BROAD PHASE SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("BROAD OPERATIONAL PHASE SUMMARY")
print("=" * 80)

phase_summary = pd.DataFrame({
    "phase": phase_columns,
    "mean_sec": [
        df[column].mean()
        for column in phase_columns
    ],
    "median_sec": [
        df[column].median()
        for column in phase_columns
    ],
    "std_sec": [
        df[column].std()
        for column in phase_columns
    ],
    "min_sec": [
        df[column].min()
        for column in phase_columns
    ],
    "max_sec": [
        df[column].max()
        for column in phase_columns
    ],
})

phase_summary["cv"] = (
    phase_summary["std_sec"]
    / phase_summary["mean_sec"]
)

print(
    phase_summary
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 11. TOTAL FLOW TIME
# =============================================================================

print("\n" + "=" * 80)
print("TOTAL PART FLOW TIME")
print("=" * 80)

total_summary = df["total_flow_time_sec"].describe()

print(
    total_summary[
        ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]
    ]
    .round(4)
    .to_string()
)


# =============================================================================
# 12. CONTRIBUTION TO TOTAL FLOW TIME
# =============================================================================

print("\n" + "=" * 80)
print("MEAN PHASE CONTRIBUTION TO TOTAL FLOW TIME")
print("=" * 80)

mean_total = df["total_flow_time_sec"].mean()

for column in phase_columns:

    mean_duration = df[column].mean()

    contribution_pct = (
        mean_duration / mean_total
    ) * 100

    print(
        f"{column:<28} "
        f"{mean_duration:>8.3f} s   "
        f"{contribution_pct:>6.2f}%"
    )


# =============================================================================
# 13. VARIABILITY RANKING
# =============================================================================

print("\n" + "=" * 80)
print("TRANSITION VARIABILITY RANKING")
print("=" * 80)

variability = transition_summary.copy()

variability = variability.sort_values(
    "std_sec",
    ascending=False
)

print(
    variability[
        [
            "stage",
            "mean_sec",
            "std_sec",
            "cv",
            "min_sec",
            "max_sec",
        ]
    ]
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 14. RELATIONSHIP WITH TOTAL FLOW TIME
# =============================================================================

print("\n" + "=" * 80)
print("TRANSITION CORRELATION WITH TOTAL FLOW TIME")
print("=" * 80)

correlations = []

for column in transition_columns:

    corr = df[column].corr(
        df["total_flow_time_sec"]
    )

    correlations.append({
        "transition": transition_labels[column],
        "correlation_with_total_flow_time": corr,
    })

correlation_df = pd.DataFrame(correlations)

correlation_df = correlation_df.sort_values(
    "correlation_with_total_flow_time",
    ascending=False
)

print(
    correlation_df
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 15. CYCLE SEQUENCE / INTER-ARRIVAL ANALYSIS
# =============================================================================

print("\n" + "=" * 80)
print("PART ARRIVAL INTERVALS")
print("=" * 80)

df["part_arrival_interval_sec"] = (
    df["PartAdded"].diff()
    / PLC_TIME_DIVISOR
)

arrival_summary = (
    df["part_arrival_interval_sec"]
    .dropna()
    .describe()
)

print(
    arrival_summary[
        ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]
    ]
    .round(4)
    .to_string()
)


# =============================================================================
# 16. OVERLAPPING PARTS IN THE CELL
# =============================================================================

print("\n" + "=" * 80)
print("PART FLOW OVERLAP")
print("=" * 80)

overlap_count = 0

for i in range(1, len(df)):

    current_part_added = df.loc[i, "PartAdded"]
    previous_part_removed = df.loc[i - 1, "PartRemoved"]

    if current_part_added < previous_part_removed:
        overlap_count += 1

print(
    f"\nConsecutive arrivals occurring before the "
    f"previous part was removed: "
    f"{overlap_count:,} of {len(df) - 1:,}"
)


# =============================================================================
# 17. SAVE ANALYTICAL DATASET
# =============================================================================

output_columns = [
    "cycle_id",
    "Part Number",
    "Work Fixture",
    "Input Position",
    "Output Position",
    "Part Type",
    "Complete",
] + transition_columns + phase_columns + [
    "total_flow_time_sec",
    "part_arrival_interval_sec",
]

output_df = df[output_columns].copy()

output_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n" + "=" * 80)
print("OUTPUT")
print("=" * 80)

print(f"\nSaved cycle-stage dataset to:")
print(OUTPUT_FILE)

print(f"\nShape: {output_df.shape}")


# =============================================================================
# 18. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
This analysis identifies where time is consumed and where cycle-to-cycle
variation occurs. It does not yet label any stage as a confirmed bottleneck.

A long stage is not automatically a bottleneck. A bottleneck interpretation
requires consideration of process necessity, variability, part overlap,
robot utilisation, waiting behaviour, and the interaction between UR3 and UR5.

The next analytical layer should therefore connect these process-stage
durations with the dual-robot telemetry.
"""
)