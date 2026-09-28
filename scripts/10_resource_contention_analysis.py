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

UR3_FILE = (
    PROJECT_ROOT
    / "data"
    / "extracted"
    / "PLC Data"
    / "UR3Data.csv"
)

UR5_FILE = (
    PROJECT_ROOT
    / "data"
    / "extracted"
    / "PLC Data"
    / "UR5Data.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "resource_contention_analysis.csv"
)


# =============================================================================
# 2. TIMEBASE CONSTANTS
# =============================================================================

# Evidence-supported analytical scale established in Script 08.
#
# IMPORTANT:
# The NIST README documents /1e7 for robot PLCTime.
# Cross-dataset timing evidence supports /1e6 for analytical alignment.
# The discrepancy remains documented rather than silently corrected.

ROBOT_PLC_DIVISOR = 1e6

# PartData process-event differences use /1e7.
PART_EVENT_DIVISOR = 1e7


# =============================================================================
# 3. PROCESS EVENTS
# =============================================================================

EVENTS = [
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


STAGES = [
    ("t1_t2", "t1", "t2"),
    ("t2_t3", "t2", "t3"),
    ("t3_t4", "t3", "t4"),
    ("t4_t5", "t4", "t5"),
    ("t5_t6", "t5", "t6"),
    ("t6_t7", "t6", "t7"),
    ("t7_t8", "t7", "t8"),
    ("t8_t9", "t8", "t9"),
    ("t9_t10", "t9", "t10"),
    ("t10_t11", "t10", "t11"),
    ("t11_t12", "t11", "t12"),
    ("t12_t13", "t12", "t13"),
    ("t13_t14", "t13", "t14"),
]


# Main waiting stages identified in the process analysis.
WAITING_STAGES = [
    "t1_t2",
    "t5_t6",
]


# =============================================================================
# 4. LOAD DATA
# =============================================================================

part = pd.read_csv(PART_FILE)
ur3 = pd.read_csv(UR3_FILE)
ur5 = pd.read_csv(UR5_FILE)

print("=" * 80)
print("NIST ROBOTIC WORK CELL - RESOURCE CONTENTION ANALYSIS")
print("=" * 80)

print(f"\nPartData rows: {len(part):,}")
print(f"UR3 rows:      {len(ur3):,}")
print(f"UR5 rows:      {len(ur5):,}")


# =============================================================================
# 5. VALIDATE PART IDENTIFIERS
# =============================================================================

print("\n" + "=" * 80)
print("PART IDENTIFIER CHECK")
print("=" * 80)

print(
    f"\nPart Number unique: "
    f"{part['Part Number'].is_unique}"
)

print(
    f"cycle_id unique:    "
    f"{part['cycle_id'].is_unique}"
)

print(
    f"Part Number range:  "
    f"{part['Part Number'].min()} -> "
    f"{part['Part Number'].max()}"
)


# =============================================================================
# 6. NORMALIZE ROBOT CLOCKS
# =============================================================================

ur3["plc_time_sec"] = (
    ur3["PLCTime"]
    / ROBOT_PLC_DIVISOR
)

ur5["plc_time_sec"] = (
    ur5["PLCTime"]
    / ROBOT_PLC_DIVISOR
)


# =============================================================================
# 7. ROBOT MOTION FEATURES
# =============================================================================

velocity_columns = [
    "j1_qdactual",
    "j2_qdactual",
    "j3_qdactual",
    "j4_qdactual",
    "j5_qdactual",
    "j6_qdactual",
]

for robot in [ur3, ur5]:

    absolute_velocity = (
        robot[velocity_columns]
        .abs()
    )

    robot["mean_abs_joint_speed"] = (
        absolute_velocity.mean(axis=1)
    )

    robot["max_abs_joint_speed"] = (
        absolute_velocity.max(axis=1)
    )


# =============================================================================
# 8. CREATE CYCLE-SPECIFIC PROCESS CLOCKS
# =============================================================================

part["ur3_anchor_sec"] = (
    part["UR3TimePartAdded"]
    / 1e6
)

part["ur5_anchor_sec"] = (
    part["UR5TimePartAdded"]
    / 1e6
)

for event_label, event_column in EVENTS:

    offset_sec = (
        part[event_column]
        - part["PartAdded"]
    ) / PART_EVENT_DIVISOR

    part[f"{event_label}_offset_sec"] = (
        offset_sec
    )

    part[f"ur3_{event_label}_sec"] = (
        part["ur3_anchor_sec"]
        + offset_sec
    )

    part[f"ur5_{event_label}_sec"] = (
        part["ur5_anchor_sec"]
        + offset_sec
    )


# =============================================================================
# 9. BUILD COMPLETE PROCESS-STAGE TABLE
# =============================================================================

stage_rows = []

for _, row in part.iterrows():

    for stage_name, start_label, end_label in STAGES:

        stage_rows.append({
            "cycle_id":
                int(row["cycle_id"]),

            "Part Number":
                row["Part Number"],

            "Work Fixture":
                row["Work Fixture"],

            "stage":
                stage_name,

            "duration_sec":
                (
                    row[f"{end_label}_offset_sec"]
                    - row[f"{start_label}_offset_sec"]
                ),

            "ur3_start_sec":
                row[f"ur3_{start_label}_sec"],

            "ur3_end_sec":
                row[f"ur3_{end_label}_sec"],

            "ur5_start_sec":
                row[f"ur5_{start_label}_sec"],

            "ur5_end_sec":
                row[f"ur5_{end_label}_sec"],
        })


stage_table = pd.DataFrame(stage_rows)

print("\n" + "=" * 80)
print("PROCESS-STAGE TABLE")
print("=" * 80)

print(
    f"\nRows: {len(stage_table):,}"
)

print(
    f"Expected: {len(part) * len(STAGES):,}"
)


# =============================================================================
# 10. OVERLAP FUNCTION
# =============================================================================

def interval_overlap(
    start_a,
    end_a,
    start_b,
    end_b,
):
    """
    Return overlap duration between two time intervals.
    """

    overlap = (
        min(end_a, end_b)
        - max(start_a, start_b)
    )

    return max(0.0, overlap)


# =============================================================================
# 11. ROBOT TELEMETRY SUMMARY FUNCTION
# =============================================================================

def telemetry_summary(
    robot,
    start_sec,
    end_sec,
):

    window = robot[
        (robot["plc_time_sec"] >= start_sec)
        & (robot["plc_time_sec"] < end_sec)
    ]

    if len(window) == 0:

        return {
            "observations": 0,
            "mean_abs_speed": np.nan,
            "p95_abs_speed": np.nan,
            "max_abs_speed": np.nan,
        }

    return {
        "observations":
            len(window),

        "mean_abs_speed":
            window[
                "mean_abs_joint_speed"
            ].mean(),

        "p95_abs_speed":
            window[
                "mean_abs_joint_speed"
            ].quantile(0.95),

        "max_abs_speed":
            window[
                "max_abs_joint_speed"
            ].max(),
    }


# =============================================================================
# 12. CONTENTION ANALYSIS
# =============================================================================

contention_rows = []

waiting_table = stage_table[
    stage_table["stage"].isin(
        WAITING_STAGES
    )
].copy()


for _, waiting in waiting_table.iterrows():

    cycle_id = int(
        waiting["cycle_id"]
    )

    waiting_stage = (
        waiting["stage"]
    )

    waiting_duration = (
        waiting["duration_sec"]
    )

    # -------------------------------------------------------------------------
    # UR3 overlap
    # -------------------------------------------------------------------------

    ur3_overlaps = []

    # -------------------------------------------------------------------------
    # UR5 overlap
    # -------------------------------------------------------------------------

    ur5_overlaps = []

    for _, other in stage_table.iterrows():

        # Exclude stages belonging to the same part.
        if (
            int(other["cycle_id"])
            == cycle_id
        ):
            continue

        ur3_overlap = interval_overlap(
            waiting["ur3_start_sec"],
            waiting["ur3_end_sec"],
            other["ur3_start_sec"],
            other["ur3_end_sec"],
        )

        ur5_overlap = interval_overlap(
            waiting["ur5_start_sec"],
            waiting["ur5_end_sec"],
            other["ur5_start_sec"],
            other["ur5_end_sec"],
        )

        if ur3_overlap > 0:

            ur3_overlaps.append({
                "other_cycle_id":
                    int(other["cycle_id"]),

                "other_part":
                    other["Part Number"],

                "other_stage":
                    other["stage"],

                "overlap_sec":
                    ur3_overlap,
            })

        if ur5_overlap > 0:

            ur5_overlaps.append({
                "other_cycle_id":
                    int(other["cycle_id"]),

                "other_part":
                    other["Part Number"],

                "other_stage":
                    other["stage"],

                "overlap_sec":
                    ur5_overlap,
            })


    # -------------------------------------------------------------------------
    # Dominant overlapping stage
    # -------------------------------------------------------------------------

    def dominant_overlap(
        overlaps,
    ):

        if not overlaps:
            return (
                None,
                0.0,
                0,
            )

        overlap_df = pd.DataFrame(
            overlaps
        )

        by_stage = (
            overlap_df
            .groupby("other_stage")[
                "overlap_sec"
            ]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        return (
            by_stage.index[0],
            by_stage.iloc[0],
            overlap_df[
                "other_cycle_id"
            ].nunique(),
        )


    (
        ur3_dominant_stage,
        ur3_dominant_overlap_sec,
        ur3_overlapping_cycles,
    ) = dominant_overlap(
        ur3_overlaps
    )

    (
        ur5_dominant_stage,
        ur5_dominant_overlap_sec,
        ur5_overlapping_cycles,
    ) = dominant_overlap(
        ur5_overlaps
    )


    # -------------------------------------------------------------------------
    # Robot telemetry during waiting interval
    # -------------------------------------------------------------------------

    ur3_activity = telemetry_summary(
        ur3,
        waiting["ur3_start_sec"],
        waiting["ur3_end_sec"],
    )

    ur5_activity = telemetry_summary(
        ur5,
        waiting["ur5_start_sec"],
        waiting["ur5_end_sec"],
    )


    contention_rows.append({
        "cycle_id":
            cycle_id,

        "Part Number":
            waiting["Part Number"],

        "Work Fixture":
            waiting["Work Fixture"],

        "waiting_stage":
            waiting_stage,

        "waiting_duration_sec":
            waiting_duration,

        "ur3_observations":
            ur3_activity[
                "observations"
            ],

        "ur3_mean_abs_speed":
            ur3_activity[
                "mean_abs_speed"
            ],

        "ur3_p95_abs_speed":
            ur3_activity[
                "p95_abs_speed"
            ],

        "ur3_dominant_other_stage":
            ur3_dominant_stage,

        "ur3_dominant_overlap_sec":
            ur3_dominant_overlap_sec,

        "ur3_overlapping_cycles":
            ur3_overlapping_cycles,

        "ur5_observations":
            ur5_activity[
                "observations"
            ],

        "ur5_mean_abs_speed":
            ur5_activity[
                "mean_abs_speed"
            ],

        "ur5_p95_abs_speed":
            ur5_activity[
                "p95_abs_speed"
            ],

        "ur5_dominant_other_stage":
            ur5_dominant_stage,

        "ur5_dominant_overlap_sec":
            ur5_dominant_overlap_sec,

        "ur5_overlapping_cycles":
            ur5_overlapping_cycles,
    })


contention = pd.DataFrame(
    contention_rows
)


# =============================================================================
# 13. WAITING-STAGE SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("WAITING-STAGE CONTENTION SUMMARY")
print("=" * 80)

summary = (
    contention
    .groupby(
        "waiting_stage",
        sort=False,
    )
    .agg(
        cycles=(
            "cycle_id",
            "count"
        ),

        mean_wait_sec=(
            "waiting_duration_sec",
            "mean"
        ),

        median_wait_sec=(
            "waiting_duration_sec",
            "median"
        ),

        sd_wait_sec=(
            "waiting_duration_sec",
            "std"
        ),

        ur3_mean_speed=(
            "ur3_mean_abs_speed",
            "mean"
        ),

        ur5_mean_speed=(
            "ur5_mean_abs_speed",
            "mean"
        ),

        ur3_mean_overlapping_cycles=(
            "ur3_overlapping_cycles",
            "mean"
        ),

        ur5_mean_overlapping_cycles=(
            "ur5_overlapping_cycles",
            "mean"
        ),
    )
    .reset_index()
)

print(
    summary
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 14. DOMINANT OVERLAPPING PROCESS STAGES
# =============================================================================

print("\n" + "=" * 80)
print("DOMINANT OVERLAPPING STAGES")
print("=" * 80)

for waiting_stage in WAITING_STAGES:

    subset = contention[
        contention[
            "waiting_stage"
        ] == waiting_stage
    ]

    print(
        f"\nWaiting stage: "
        f"{waiting_stage}"
    )

    print("\nUR3 clock-domain overlaps:")

    print(
        subset[
            "ur3_dominant_other_stage"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print("\nUR5 clock-domain overlaps:")

    print(
        subset[
            "ur5_dominant_other_stage"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )


# =============================================================================
# 15. LONGEST WAITING CYCLES
# =============================================================================

print("\n" + "=" * 80)
print("LONGEST WAITING CYCLES")
print("=" * 80)

for waiting_stage in WAITING_STAGES:

    print(
        f"\nTop 10 longest waits: "
        f"{waiting_stage}"
    )

    columns = [
        "cycle_id",
        "Part Number",
        "Work Fixture",
        "waiting_duration_sec",
        "ur3_mean_abs_speed",
        "ur5_mean_abs_speed",
        "ur3_dominant_other_stage",
        "ur3_dominant_overlap_sec",
        "ur5_dominant_other_stage",
        "ur5_dominant_overlap_sec",
    ]

    print(
        contention[
            contention[
                "waiting_stage"
            ] == waiting_stage
        ][columns]
        .sort_values(
            "waiting_duration_sec",
            ascending=False,
        )
        .head(10)
        .round(4)
        .to_string(index=False)
    )


# =============================================================================
# 16. WAIT DURATION vs ROBOT ACTIVITY
# =============================================================================

print("\n" + "=" * 80)
print("WAIT DURATION vs ROBOT ACTIVITY")
print("=" * 80)

for waiting_stage in WAITING_STAGES:

    subset = contention[
        contention[
            "waiting_stage"
        ] == waiting_stage
    ]

    print(
        f"\n{waiting_stage}"
    )

    print(
        "Correlation with UR3 mean speed: "
        f"{subset['waiting_duration_sec'].corr(subset['ur3_mean_abs_speed']):.4f}"
    )

    print(
        "Correlation with UR5 mean speed: "
        f"{subset['waiting_duration_sec'].corr(subset['ur5_mean_abs_speed']):.4f}"
    )


# =============================================================================
# 17. WAIT DURATION vs OVERLAP
# =============================================================================

print("\n" + "=" * 80)
print("WAIT DURATION vs DOMINANT OVERLAP")
print("=" * 80)

for waiting_stage in WAITING_STAGES:

    subset = contention[
        contention[
            "waiting_stage"
        ] == waiting_stage
    ]

    print(
        f"\n{waiting_stage}"
    )

    print(
        "Correlation with UR3 dominant overlap: "
        f"{subset['waiting_duration_sec'].corr(subset['ur3_dominant_overlap_sec']):.4f}"
    )

    print(
        "Correlation with UR5 dominant overlap: "
        f"{subset['waiting_duration_sec'].corr(subset['ur5_dominant_overlap_sec']):.4f}"
    )


# =============================================================================
# 18. SAVE
# =============================================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

contention.to_csv(
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
    f"{contention.shape}"
)


# =============================================================================
# 19. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
This analysis tests whether the two major waiting intervals overlap
with processing stages belonging to other parts in the pipelined cell.

An overlap means that another part is simultaneously somewhere within
its process timeline. It does NOT by itself prove that a specific robot
is physically responsible for that overlapping stage.

Robot mean absolute joint speed is therefore retained as an independent
activity indicator.

The purpose of this analysis is to distinguish:

1. apparent waiting caused by the pipelined production structure,
2. possible resource-contention or synchronization effects, and
3. genuinely unexplained waiting.

No bottleneck or causal mechanism should be declared from temporal
overlap alone.
"""
)