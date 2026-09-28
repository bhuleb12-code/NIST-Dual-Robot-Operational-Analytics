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
    / "process_robot_alignment.csv"
)


# =============================================================================
# 2. CONSTANTS
# =============================================================================

# IMPORTANT:
#
# The NIST README documents PLCTime / 1e7.
#
# Script 08 identified a timing-scale discrepancy. Multiple independent
# experiment-level references support /1e6 for analytical alignment:
#
# - UR3 PLC duration ≈ 45.50 min
# - UR5 PLC duration ≈ 45.50 min
# - UR5 RTDE duration ≈ 45.11 min
# - documented collection window ≈ 48 min
# - Part 1 occurs ≈ 22 sec after PLC collection begins
#
# Therefore /1e6 is used here as the evidence-supported analytical scale.
# The source documentation discrepancy must remain documented.

PLC_ANALYTICAL_DIVISOR = 1e6

# PartData PLC event timestamps were previously shown to produce
# physically plausible stage durations using /1e7.

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
    ("t1_t2", "PartAdded", "PickFromInputAssigned"),
    ("t2_t3", "PickFromInputAssigned", "InputPartPicked"),
    ("t3_t4", "InputPartPicked", "InputPartPlaced"),
    ("t4_t5", "InputPartPlaced", "PlaceInWFComplete"),
    ("t5_t6", "PlaceInWFComplete", "TaskAssigned"),
    ("t6_t7", "TaskAssigned", "TaskActionStart"),
    ("t7_t8", "TaskActionStart", "TaskActionComplete"),
    ("t8_t9", "TaskActionComplete", "TaskComplete"),
    ("t9_t10", "TaskComplete", "PickFromWFAssigned"),
    ("t10_t11", "PickFromWFAssigned", "OutputPartPicked"),
    ("t11_t12", "OutputPartPicked", "PutputPartPlaced"),
    ("t12_t13", "PutputPartPlaced", "PlaceInOutputComplete"),
    ("t13_t14", "PlaceInOutputComplete", "PartRemoved"),
]


# =============================================================================
# 4. LOAD DATA
# =============================================================================

part = pd.read_csv(PART_FILE)
ur3 = pd.read_csv(UR3_FILE)
ur5 = pd.read_csv(UR5_FILE)

print("=" * 80)
print("NIST FULL PROCESS - DUAL ROBOT ALIGNMENT")
print("=" * 80)

print(f"\nPartData rows: {len(part):,}")
print(f"UR3 rows:      {len(ur3):,}")
print(f"UR5 rows:      {len(ur5):,}")


# =============================================================================
# 5. VALIDATE REQUIRED FIELDS
# =============================================================================

required_part_columns = [
    "cycle_id",
    "Part Number",
    "Work Fixture",
    "UR3TimePartAdded",
    "UR5TimePartAdded",
] + [column for _, column in EVENTS]

for column in required_part_columns:
    if column not in part.columns:
        raise ValueError(
            f"Required PartData field missing: {column}"
        )

velocity_columns = [
    "j1_qdactual",
    "j2_qdactual",
    "j3_qdactual",
    "j4_qdactual",
    "j5_qdactual",
    "j6_qdactual",
]

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:
    for column in ["PLCTime"] + velocity_columns:
        if column not in robot.columns:
            raise ValueError(
                f"{robot_name} missing field: {column}"
            )


# =============================================================================
# 6. NORMALIZE ROBOT PLC CLOCKS
# =============================================================================

ur3["plc_time_sec"] = (
    ur3["PLCTime"]
    / PLC_ANALYTICAL_DIVISOR
)

ur5["plc_time_sec"] = (
    ur5["PLCTime"]
    / PLC_ANALYTICAL_DIVISOR
)

print("\n" + "=" * 80)
print("ROBOT TELEMETRY CLOCK RANGES")
print("=" * 80)

print(
    f"\nUR3: "
    f"{ur3['plc_time_sec'].iloc[0]:.6f} -> "
    f"{ur3['plc_time_sec'].iloc[-1]:.6f} sec"
)

print(
    f"UR5: "
    f"{ur5['plc_time_sec'].iloc[0]:.6f} -> "
    f"{ur5['plc_time_sec'].iloc[-1]:.6f} sec"
)


# =============================================================================
# 7. CREATE ROBOT ACTIVITY FEATURES
# =============================================================================

for robot in [ur3, ur5]:

    abs_velocity = (
        robot[velocity_columns]
        .abs()
    )

    robot["joint_speed_abs_mean"] = (
        abs_velocity.mean(axis=1)
    )

    robot["joint_speed_abs_max"] = (
        abs_velocity.max(axis=1)
    )

    robot["joint_speed_abs_sum"] = (
        abs_velocity.sum(axis=1)
    )


# =============================================================================
# 8. PARTDATA CLOCK BRIDGE
# =============================================================================

# PartData contains robot-clock timestamps for the moment each part
# was added. These provide cycle-specific anchors between the PartData
# process record and each robot's PLC time domain.

part["ur3_anchor_sec"] = (
    part["UR3TimePartAdded"]
    / 1e6
)

part["ur5_anchor_sec"] = (
    part["UR5TimePartAdded"]
    / 1e6
)

# The process event timestamps use a different PLC time representation.
# We therefore align process events relative to PartAdded for each cycle.
#
# Example:
#   t7 robot time =
#       robot PartAdded anchor
#       + (TaskActionStart - PartAdded) / 1e7
#
# This avoids assuming that the absolute PartData PLC event timestamp
# is directly expressed in the robot telemetry clock domain.

for event_label, event_column in EVENTS:

    relative_offset = (
        part[event_column]
        - part["PartAdded"]
    ) / PART_EVENT_DIVISOR

    part[f"{event_label}_offset_sec"] = (
        relative_offset
    )

    part[f"ur3_{event_label}_sec"] = (
        part["ur3_anchor_sec"]
        + relative_offset
    )

    part[f"ur5_{event_label}_sec"] = (
        part["ur5_anchor_sec"]
        + relative_offset
    )


# =============================================================================
# 9. EVENT CLOCK SANITY CHECK
# =============================================================================

print("\n" + "=" * 80)
print("EVENT CLOCK SANITY CHECK")
print("=" * 80)

print(
    "\nRelative process duration t1 -> t14:"
)

total_duration = (
    part["t14_offset_sec"]
    - part["t1_offset_sec"]
)

print(
    total_duration.describe()
    .round(4)
    .to_string()
)

print(
    "\nFirst five cycle anchors:"
)

print(
    part[
        [
            "cycle_id",
            "Part Number",
            "ur3_anchor_sec",
            "ur5_anchor_sec",
            "t14_offset_sec",
        ]
    ]
    .head()
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 10. TEST EVENT COVERAGE INSIDE TELEMETRY
# =============================================================================

print("\n" + "=" * 80)
print("PROCESS EVENT COVERAGE")
print("=" * 80)


def event_coverage(robot, robot_name):

    robot_start = (
        robot["plc_time_sec"].min()
    )

    robot_end = (
        robot["plc_time_sec"].max()
    )

    results = []

    for event_label, event_column in EVENTS:

        event_times = (
            part[
                f"{robot_name.lower()}_{event_label}_sec"
            ]
        )

        inside = (
            (event_times >= robot_start)
            & (event_times <= robot_end)
        )

        results.append({
            "event": event_label,
            "event_name": event_column,
            "inside": int(inside.sum()),
            "outside": int((~inside).sum()),
            "coverage_pct":
                inside.mean() * 100,
        })

    result_df = pd.DataFrame(results)

    print(f"\n{robot_name}")

    print(
        result_df
        .round(2)
        .to_string(index=False)
    )

    return result_df


ur3_event_coverage = event_coverage(
    ur3,
    "UR3"
)

ur5_event_coverage = event_coverage(
    ur5,
    "UR5"
)


# =============================================================================
# 11. STAGE-LEVEL ROBOT SUMMARY FUNCTION
# =============================================================================

def summarize_stage(
    robot,
    start_time,
    end_time,
):

    window = robot[
        (robot["plc_time_sec"] >= start_time)
        & (robot["plc_time_sec"] < end_time)
    ]

    if len(window) == 0:
        return {
            "observations": 0,
            "mean_abs_speed": np.nan,
            "median_abs_speed": np.nan,
            "p95_abs_speed": np.nan,
            "max_abs_speed": np.nan,
        }

    return {
        "observations":
            len(window),

        "mean_abs_speed":
            window[
                "joint_speed_abs_mean"
            ].mean(),

        "median_abs_speed":
            window[
                "joint_speed_abs_mean"
            ].median(),

        "p95_abs_speed":
            window[
                "joint_speed_abs_mean"
            ].quantile(0.95),

        "max_abs_speed":
            window[
                "joint_speed_abs_max"
            ].max(),
    }


# =============================================================================
# 12. ALIGN EVERY CYCLE/STAGE WITH BOTH ROBOTS
# =============================================================================

alignment_rows = []

for _, row in part.iterrows():

    for (
        stage_name,
        start_event,
        end_event,
    ) in STAGES:

        start_label = next(
            label
            for label, column in EVENTS
            if column == start_event
        )

        end_label = next(
            label
            for label, column in EVENTS
            if column == end_event
        )

        stage_duration = (
            row[f"{end_label}_offset_sec"]
            - row[f"{start_label}_offset_sec"]
        )

        ur3_start = (
            row[
                f"ur3_{start_label}_sec"
            ]
        )

        ur3_end = (
            row[
                f"ur3_{end_label}_sec"
            ]
        )

        ur5_start = (
            row[
                f"ur5_{start_label}_sec"
            ]
        )

        ur5_end = (
            row[
                f"ur5_{end_label}_sec"
            ]
        )

        ur3_summary = summarize_stage(
            ur3,
            ur3_start,
            ur3_end,
        )

        ur5_summary = summarize_stage(
            ur5,
            ur5_start,
            ur5_end,
        )

        alignment_rows.append({
            "cycle_id":
                int(row["cycle_id"]),

            "Part Number":
                row["Part Number"],

            "Work Fixture":
                row["Work Fixture"],

            "stage":
                stage_name,

            "start_event":
                start_event,

            "end_event":
                end_event,

            "stage_duration_sec":
                stage_duration,

            "ur3_start_sec":
                ur3_start,

            "ur3_end_sec":
                ur3_end,

            "ur3_observations":
                ur3_summary[
                    "observations"
                ],

            "ur3_mean_abs_speed":
                ur3_summary[
                    "mean_abs_speed"
                ],

            "ur3_median_abs_speed":
                ur3_summary[
                    "median_abs_speed"
                ],

            "ur3_p95_abs_speed":
                ur3_summary[
                    "p95_abs_speed"
                ],

            "ur3_max_abs_speed":
                ur3_summary[
                    "max_abs_speed"
                ],

            "ur5_start_sec":
                ur5_start,

            "ur5_end_sec":
                ur5_end,

            "ur5_observations":
                ur5_summary[
                    "observations"
                ],

            "ur5_mean_abs_speed":
                ur5_summary[
                    "mean_abs_speed"
                ],

            "ur5_median_abs_speed":
                ur5_summary[
                    "median_abs_speed"
                ],

            "ur5_p95_abs_speed":
                ur5_summary[
                    "p95_abs_speed"
                ],

            "ur5_max_abs_speed":
                ur5_summary[
                    "max_abs_speed"
                ],
        })


alignment = pd.DataFrame(
    alignment_rows
)


# =============================================================================
# 13. ALIGNMENT COVERAGE
# =============================================================================

print("\n" + "=" * 80)
print("STAGE ALIGNMENT COVERAGE")
print("=" * 80)

expected_rows = (
    len(part)
    * len(STAGES)
)

print(
    f"\nExpected cycle-stage rows: "
    f"{expected_rows:,}"
)

print(
    f"Actual cycle-stage rows:   "
    f"{len(alignment):,}"
)

ur3_with_data = (
    alignment["ur3_observations"]
    > 0
)

ur5_with_data = (
    alignment["ur5_observations"]
    > 0
)

both_with_data = (
    ur3_with_data
    & ur5_with_data
)

print(
    f"\nUR3 stages with telemetry: "
    f"{ur3_with_data.sum():,} "
    f"({ur3_with_data.mean() * 100:.2f}%)"
)

print(
    f"UR5 stages with telemetry: "
    f"{ur5_with_data.sum():,} "
    f"({ur5_with_data.mean() * 100:.2f}%)"
)

print(
    f"Both robots available:     "
    f"{both_with_data.sum():,} "
    f"({both_with_data.mean() * 100:.2f}%)"
)


# =============================================================================
# 14. STAGE-LEVEL DUAL-ROBOT PROFILE
# =============================================================================

print("\n" + "=" * 80)
print("STAGE-LEVEL DUAL-ROBOT ACTIVITY PROFILE")
print("=" * 80)

stage_profile = (
    alignment
    .groupby(
        [
            "stage",
            "start_event",
            "end_event",
        ],
        sort=False,
    )
    .agg(
        cycles=(
            "cycle_id",
            "count"
        ),

        mean_stage_duration_sec=(
            "stage_duration_sec",
            "mean"
        ),

        median_stage_duration_sec=(
            "stage_duration_sec",
            "median"
        ),

        ur3_mean_abs_speed=(
            "ur3_mean_abs_speed",
            "mean"
        ),

        ur5_mean_abs_speed=(
            "ur5_mean_abs_speed",
            "mean"
        ),

        ur3_mean_observations=(
            "ur3_observations",
            "mean"
        ),

        ur5_mean_observations=(
            "ur5_observations",
            "mean"
        ),
    )
    .reset_index()
)

print(
    stage_profile
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 15. ROBOT ACTIVITY DIFFERENCE BY STAGE
# =============================================================================

stage_profile[
    "ur3_minus_ur5_speed"
] = (
    stage_profile[
        "ur3_mean_abs_speed"
    ]
    - stage_profile[
        "ur5_mean_abs_speed"
    ]
)

print("\n" + "=" * 80)
print("RELATIVE ROBOT ACTIVITY BY PROCESS STAGE")
print("=" * 80)

print(
    stage_profile[
        [
            "stage",
            "mean_stage_duration_sec",
            "ur3_mean_abs_speed",
            "ur5_mean_abs_speed",
            "ur3_minus_ur5_speed",
        ]
    ]
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 16. WAITING-STAGE PROFILE
# =============================================================================

print("\n" + "=" * 80)
print("WAITING-STAGE DUAL-ROBOT PROFILE")
print("=" * 80)

waiting_stages = [
    "t1_t2",
    "t5_t6",
]

waiting_profile = (
    alignment[
        alignment["stage"].isin(
            waiting_stages
        )
    ]
    .groupby(
        "stage",
        sort=False,
    )
    .agg(
        cycles=(
            "cycle_id",
            "count"
        ),

        mean_duration_sec=(
            "stage_duration_sec",
            "mean"
        ),

        sd_duration_sec=(
            "stage_duration_sec",
            "std"
        ),

        ur3_mean_abs_speed=(
            "ur3_mean_abs_speed",
            "mean"
        ),

        ur5_mean_abs_speed=(
            "ur5_mean_abs_speed",
            "mean"
        ),
    )
    .reset_index()
)

print(
    waiting_profile
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 17. TASK-ACTION PROFILE
# =============================================================================

print("\n" + "=" * 80)
print("TASK-ACTION DUAL-ROBOT PROFILE")
print("=" * 80)

task_profile = (
    alignment[
        alignment["stage"]
        == "t7_t8"
    ][
        [
            "cycle_id",
            "Part Number",
            "Work Fixture",
            "stage_duration_sec",
            "ur3_observations",
            "ur3_mean_abs_speed",
            "ur5_observations",
            "ur5_mean_abs_speed",
        ]
    ]
)

print(
    task_profile
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 18. SAVE ALIGNED DATASET
# =============================================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

alignment.to_csv(
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
    f"{alignment.shape}"
)


# =============================================================================
# 19. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
This alignment uses cycle-specific PartData robot timestamps as anchors.

Process-event timestamps are translated into each robot clock by their
relative offset from PartAdded. This avoids directly equating the
absolute PartData PLC-event clock with the robot telemetry clock.

The robot PLCTime analytical scale used here is /1e6. This differs from
the /1e7 divisor documented in the NIST README. The analytical choice
is based on the independent timing consistency established in Script 08
and must remain explicitly documented as a source-data timing discrepancy.

Mean absolute joint speed is used here only as a continuous activity
indicator. No moving/idle threshold is imposed.

Stage-level robot activity can now be compared with process-stage
duration, but activity alone does not prove the cause of waiting time.
"""
)