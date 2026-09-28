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
    / "bottleneck_cycle_decomposition.csv"
)


# =============================================================================
# 2. CONSTANTS
# =============================================================================

EVENT_DIVISOR = 1e7
ROBOT_PLC_DIVISOR = 1e6

# Script 11 established Parts 6-55 as the central production window.
CENTRAL_START = 6
CENTRAL_END = 55


# =============================================================================
# 3. LOAD
# =============================================================================

part = pd.read_csv(PART_FILE)
ur3 = pd.read_csv(UR3_FILE)
ur5 = pd.read_csv(UR5_FILE)

part = (
    part
    .sort_values("Part Number")
    .reset_index(drop=True)
)

print("=" * 80)
print("NIST ROBOTIC WORK CELL - BOTTLENECK CYCLE DECOMPOSITION")
print("=" * 80)

print(f"\nParts:    {len(part):,}")
print(f"UR3 rows: {len(ur3):,}")
print(f"UR5 rows: {len(ur5):,}")


# =============================================================================
# 4. EVENT TIMES
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
# 5. TASK-CYCLE COMPONENTS
# =============================================================================

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


# =============================================================================
# 6. CONSECUTIVE TASK RELATIONSHIPS
# =============================================================================

# For Part n, compare its task execution with Part n+1.
#
# Example:
#
# Part n:
#     TaskActionStart ---------------- TaskActionComplete
#
# Part n+1:
#                                      ... TaskAssigned
#                                          TaskActionStart
#
# We want to know what occupies the time between completion of one
# task action and start of the next task action.

part["next_part_number"] = (
    part["Part Number"]
    .shift(-1)
)

part["next_work_fixture"] = (
    part["Work Fixture"]
    .shift(-1)
)

part["next_task_assigned_sec"] = (
    part["TaskAssigned_sec"]
    .shift(-1)
)

part["next_task_start_sec"] = (
    part["TaskActionStart_sec"]
    .shift(-1)
)

part["next_task_complete_sec"] = (
    part["TaskActionComplete_sec"]
    .shift(-1)
)


# =============================================================================
# 7. INTER-TASK GAP
# =============================================================================

part["task_complete_to_next_assigned_sec"] = (
    part["next_task_assigned_sec"]
    - part["TaskActionComplete_sec"]
)

part["next_assigned_to_next_start_sec"] = (
    part["next_task_start_sec"]
    - part["next_task_assigned_sec"]
)

part["task_complete_to_next_start_sec"] = (
    part["next_task_start_sec"]
    - part["TaskActionComplete_sec"]
)

part["task_start_to_next_task_start_sec"] = (
    part["next_task_start_sec"]
    - part["TaskActionStart_sec"]
)


# =============================================================================
# 8. CENTRAL TRANSITIONS
# =============================================================================

# We use transitions whose current and next part both belong to the
# central production window.

central = part[
    (part["Part Number"] >= CENTRAL_START)
    & (part["next_part_number"] <= CENTRAL_END)
].copy()

print("\n" + "=" * 80)
print("CENTRAL TASK TRANSITIONS")
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
# 9. TASK HEARTBEAT SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("TASK HEARTBEAT DECOMPOSITION")
print("=" * 80)

metrics = [
    "task_action_sec",
    "task_complete_to_next_assigned_sec",
    "next_assigned_to_next_start_sec",
    "task_complete_to_next_start_sec",
    "task_start_to_next_task_start_sec",
]

summary_rows = []

for metric in metrics:

    values = (
        central[metric]
        .dropna()
    )

    summary_rows.append({
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
    })

summary = pd.DataFrame(
    summary_rows
)

print(
    summary
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 10. MATHEMATICAL RECONCILIATION
# =============================================================================

print("\n" + "=" * 80)
print("TASK HEARTBEAT RECONCILIATION")
print("=" * 80)

mean_task_action = (
    central["task_action_sec"]
    .mean()
)

mean_intertask_gap = (
    central[
        "task_complete_to_next_start_sec"
    ]
    .mean()
)

mean_task_start_interval = (
    central[
        "task_start_to_next_task_start_sec"
    ]
    .mean()
)

reconstructed = (
    mean_task_action
    + mean_intertask_gap
)

print(
    f"\nMean task action:              "
    f"{mean_task_action:.4f} sec"
)

print(
    f"Mean complete -> next start:   "
    f"{mean_intertask_gap:.4f} sec"
)

print(
    f"Sum:                           "
    f"{reconstructed:.4f} sec"
)

print(
    f"Observed TaskStart -> TaskStart:"
    f" {mean_task_start_interval:.4f} sec"
)

print(
    f"Reconciliation difference:     "
    f"{reconstructed - mean_task_start_interval:.8f} sec"
)


# =============================================================================
# 11. DECOMPOSE INTER-TASK GAP
# =============================================================================

print("\n" + "=" * 80)
print("INTER-TASK GAP COMPONENTS")
print("=" * 80)

gap_component_1 = (
    central[
        "task_complete_to_next_assigned_sec"
    ]
    .mean()
)

gap_component_2 = (
    central[
        "next_assigned_to_next_start_sec"
    ]
    .mean()
)

gap_total = (
    central[
        "task_complete_to_next_start_sec"
    ]
    .mean()
)

print(
    f"\nPrevious TaskActionComplete "
    f"-> next TaskAssigned:"
    f" {gap_component_1:.4f} sec"
)

print(
    f"Next TaskAssigned "
    f"-> next TaskActionStart:"
    f" {gap_component_2:.4f} sec"
)

print(
    f"Total inter-task gap:          "
    f"{gap_total:.4f} sec"
)

if gap_total != 0:

    print(
        f"\nShare before TaskAssigned: "
        f"{gap_component_1 / gap_total * 100:.2f}%"
    )

    print(
        f"Share after TaskAssigned:  "
        f"{gap_component_2 / gap_total * 100:.2f}%"
    )


# =============================================================================
# 12. FIXTURE-TO-FIXTURE TRANSITIONS
# =============================================================================

print("\n" + "=" * 80)
print("FIXTURE-TO-FIXTURE TASK TRANSITIONS")
print("=" * 80)

fixture_transition = (
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

        mean_task_action_sec=(
            "task_action_sec",
            "mean"
        ),

        mean_intertask_gap_sec=(
            "task_complete_to_next_start_sec",
            "mean"
        ),

        sd_intertask_gap_sec=(
            "task_complete_to_next_start_sec",
            "std"
        ),

        mean_task_heartbeat_sec=(
            "task_start_to_next_task_start_sec",
            "mean"
        ),

        sd_task_heartbeat_sec=(
            "task_start_to_next_task_start_sec",
            "std"
        ),
    )
    .reset_index()
)

print(
    fixture_transition
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 13. PART-BY-PART DECOMPOSITION
# =============================================================================

print("\n" + "=" * 80)
print("PART-BY-PART TASK CYCLE")
print("=" * 80)

display_columns = [
    "Part Number",
    "Work Fixture",
    "next_part_number",
    "next_work_fixture",
    "task_action_sec",
    "task_complete_to_next_assigned_sec",
    "next_assigned_to_next_start_sec",
    "task_complete_to_next_start_sec",
    "task_start_to_next_task_start_sec",
]

print(
    central[
        display_columns
    ]
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 14. ROBOT CLOCK PREPARATION
# =============================================================================

ur3["plc_time_sec"] = (
    ur3["PLCTime"]
    / ROBOT_PLC_DIVISOR
)

ur5["plc_time_sec"] = (
    ur5["PLCTime"]
    / ROBOT_PLC_DIVISOR
)

velocity_columns = [
    "j1_qdactual",
    "j2_qdactual",
    "j3_qdactual",
    "j4_qdactual",
    "j5_qdactual",
    "j6_qdactual",
]

for robot in [ur3, ur5]:

    robot["mean_abs_joint_speed"] = (
        robot[
            velocity_columns
        ]
        .abs()
        .mean(axis=1)
    )


# =============================================================================
# 15. MAP INTER-TASK GAP INTO ROBOT CLOCKS
# =============================================================================

# The PartData robot timestamps anchor PartAdded into each robot clock.
# As in Script 09, process-event offsets are then added to the anchor.

part["ur3_anchor_sec"] = (
    part["UR3TimePartAdded"]
    / 1e6
)

part["ur5_anchor_sec"] = (
    part["UR5TimePartAdded"]
    / 1e6
)

part["task_start_offset_sec"] = (
    (
        part["TaskActionStart"]
        - part["PartAdded"]
    )
    / EVENT_DIVISOR
)

part["task_complete_offset_sec"] = (
    (
        part["TaskActionComplete"]
        - part["PartAdded"]
    )
    / EVENT_DIVISOR
)

part["ur3_task_start_sec"] = (
    part["ur3_anchor_sec"]
    + part["task_start_offset_sec"]
)

part["ur3_task_complete_sec"] = (
    part["ur3_anchor_sec"]
    + part["task_complete_offset_sec"]
)

part["ur5_task_start_sec"] = (
    part["ur5_anchor_sec"]
    + part["task_start_offset_sec"]
)

part["ur5_task_complete_sec"] = (
    part["ur5_anchor_sec"]
    + part["task_complete_offset_sec"]
)

part["next_ur3_task_start_sec"] = (
    part["ur3_task_start_sec"]
    .shift(-1)
)

part["next_ur5_task_start_sec"] = (
    part["ur5_task_start_sec"]
    .shift(-1)
)


# Rebuild central after robot-clock fields are created.

central_robot = part[
    (part["Part Number"] >= CENTRAL_START)
    & (part["next_part_number"] <= CENTRAL_END)
].copy()


# =============================================================================
# 16. ROBOT ACTIVITY DURING INTER-TASK GAP
# =============================================================================

def summarize_robot_window(
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
            "mean_speed": np.nan,
            "median_speed": np.nan,
            "p95_speed": np.nan,
        }

    return {
        "observations":
            len(window),

        "mean_speed":
            window[
                "mean_abs_joint_speed"
            ].mean(),

        "median_speed":
            window[
                "mean_abs_joint_speed"
            ].median(),

        "p95_speed":
            window[
                "mean_abs_joint_speed"
            ].quantile(0.95),
    }


robot_gap_rows = []

for _, row in central_robot.iterrows():

    ur3_summary = summarize_robot_window(
        ur3,
        row["ur3_task_complete_sec"],
        row["next_ur3_task_start_sec"],
    )

    ur5_summary = summarize_robot_window(
        ur5,
        row["ur5_task_complete_sec"],
        row["next_ur5_task_start_sec"],
    )

    robot_gap_rows.append({
        "Part Number":
            row["Part Number"],

        "Work Fixture":
            row["Work Fixture"],

        "next_part_number":
            row["next_part_number"],

        "next_work_fixture":
            row["next_work_fixture"],

        "intertask_gap_sec":
            row[
                "task_complete_to_next_start_sec"
            ],

        "ur3_observations":
            ur3_summary["observations"],

        "ur3_mean_speed":
            ur3_summary["mean_speed"],

        "ur3_median_speed":
            ur3_summary["median_speed"],

        "ur3_p95_speed":
            ur3_summary["p95_speed"],

        "ur5_observations":
            ur5_summary["observations"],

        "ur5_mean_speed":
            ur5_summary["mean_speed"],

        "ur5_median_speed":
            ur5_summary["median_speed"],

        "ur5_p95_speed":
            ur5_summary["p95_speed"],
    })


robot_gap = pd.DataFrame(
    robot_gap_rows
)


print("\n" + "=" * 80)
print("ROBOT ACTIVITY DURING INTER-TASK GAP")
print("=" * 80)

robot_gap_summary = (
    robot_gap
    .agg(
        {
            "intertask_gap_sec": [
                "mean",
                "std",
            ],

            "ur3_observations": [
                "mean",
            ],

            "ur3_mean_speed": [
                "mean",
            ],

            "ur3_p95_speed": [
                "mean",
            ],

            "ur5_observations": [
                "mean",
            ],

            "ur5_mean_speed": [
                "mean",
            ],

            "ur5_p95_speed": [
                "mean",
            ],
        }
    )
)

print(
    robot_gap_summary
    .round(4)
    .to_string()
)


# =============================================================================
# 17. ROBOT ACTIVITY BY FIXTURE TRANSITION
# =============================================================================

print("\n" + "=" * 80)
print("ROBOT ACTIVITY BY FIXTURE TRANSITION")
print("=" * 80)

robot_fixture = (
    robot_gap
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

        mean_gap_sec=(
            "intertask_gap_sec",
            "mean"
        ),

        ur3_mean_speed=(
            "ur3_mean_speed",
            "mean"
        ),

        ur5_mean_speed=(
            "ur5_mean_speed",
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
    robot_fixture
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 18. SAVE
# =============================================================================

output = central[
    display_columns
].copy()

robot_columns = [
    "Part Number",
    "ur3_observations",
    "ur3_mean_speed",
    "ur3_median_speed",
    "ur3_p95_speed",
    "ur5_observations",
    "ur5_mean_speed",
    "ur5_median_speed",
    "ur5_p95_speed",
]

output = output.merge(
    robot_gap[
        robot_columns
    ],
    on="Part Number",
    how="left",
)

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
# 19. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
This analysis decomposes the recurring TaskStart-to-TaskStart production
heartbeat into:

    current task action
    +
    TaskActionComplete-to-next-TaskActionStart gap

The inter-task gap is further separated into:

    previous TaskActionComplete -> next TaskAssigned
    +
    next TaskAssigned -> next TaskActionStart

These intervals are descriptive process timings. Their existence does
not by itself prove avoidable delay.

Robot activity during the inter-task gap is also measured, but mean
joint speed does not by itself identify resource ownership or causality.

A bottleneck conclusion should only be made if the timing structure,
resource behaviour and repeated production cadence support the same
interpretation.
"""
)