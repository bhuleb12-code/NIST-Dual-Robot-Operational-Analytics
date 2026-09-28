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
    / "robot_motion_signature_analysis.csv"
)


# =============================================================================
# 2. CONSTANTS
# =============================================================================

ROBOT_PLC_DIVISOR = 1e6
EVENT_DIVISOR = 1e7

CENTRAL_START = 6
CENTRAL_END = 55


# =============================================================================
# 3. FINE-GRAINED PROCESS WINDOWS
# =============================================================================

# These correspond directly to the documented process timeline.
#
# No robot ownership is assumed.

PROCESS_WINDOWS = [
    (
        "t2_t3",
        "PickFromInputAssigned",
        "InputPartPicked",
        "input_pick"
    ),
    (
        "t3_t4",
        "InputPartPicked",
        "InputPartPlaced",
        "input_transfer"
    ),
    (
        "t4_t5",
        "InputPartPlaced",
        "PlaceInWFComplete",
        "input_completion"
    ),
    (
        "t6_t7",
        "TaskAssigned",
        "TaskActionStart",
        "pre_task"
    ),
    (
        "t7_t8",
        "TaskActionStart",
        "TaskActionComplete",
        "task_action"
    ),
    (
        "t8_t9",
        "TaskActionComplete",
        "TaskComplete",
        "post_task"
    ),
    (
        "t10_t11",
        "PickFromWFAssigned",
        "OutputPartPicked",
        "output_pick"
    ),
    (
        "t11_t12",
        "OutputPartPicked",
        "PutputPartPlaced",
        "output_transfer"
    ),
    (
        "t12_t13",
        "PutputPartPlaced",
        "PlaceInOutputComplete",
        "output_completion"
    ),
]


# =============================================================================
# 4. LOAD
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
print("NIST ROBOTIC WORK CELL - ROBOT MOTION SIGNATURE ANALYSIS")
print("=" * 80)

print(f"\nPartData rows: {len(part):,}")
print(f"UR3 rows:      {len(ur3):,}")
print(f"UR5 rows:      {len(ur5):,}")


# =============================================================================
# 5. ROBOT CLOCKS
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
# 6. SIGNALS
# =============================================================================

JOINT_COLUMNS = [
    "j1_qactual",
    "j2_qactual",
    "j3_qactual",
    "j4_qactual",
    "j5_qactual",
    "j6_qactual",
]

XY_COLUMNS = [
    "ToolX",
    "ToolY",
]


# =============================================================================
# 7. VERIFY XY SIGNALS
# =============================================================================

print("\n" + "=" * 80)
print("XY TOOL SIGNAL AVAILABILITY")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    print(f"\n{robot_name}")

    for column in XY_COLUMNS:

        print(
            f"{column}: "
            f"non-null={robot[column].notna().sum():,}, "
            f"unique={robot[column].nunique(dropna=True):,}"
        )


# =============================================================================
# 8. PART-SPECIFIC ROBOT CLOCKS
# =============================================================================

part["ur3_anchor_sec"] = (
    part["UR3TimePartAdded"]
    / 1e6
)

part["ur5_anchor_sec"] = (
    part["UR5TimePartAdded"]
    / 1e6
)


required_events = set()

for (
    stage,
    start_event,
    end_event,
    process_family,
) in PROCESS_WINDOWS:

    required_events.add(start_event)
    required_events.add(end_event)


for event in sorted(required_events):

    offset = (
        part[event]
        - part["PartAdded"]
    ) / EVENT_DIVISOR

    part[
        f"ur3_{event}_sec"
    ] = (
        part["ur3_anchor_sec"]
        + offset
    )

    part[
        f"ur5_{event}_sec"
    ] = (
        part["ur5_anchor_sec"]
        + offset
    )


# =============================================================================
# 9. CENTRAL PRODUCTION WINDOW
# =============================================================================

central = part[
    part["Part Number"].between(
        CENTRAL_START,
        CENTRAL_END,
    )
].copy()

print("\n" + "=" * 80)
print("ANALYTICAL WINDOW")
print("=" * 80)

print(
    f"\nParts: "
    f"{CENTRAL_START}-{CENTRAL_END}"
)

print(
    f"Number of parts: "
    f"{len(central)}"
)


# =============================================================================
# 10. MOTION SUMMARY FUNCTION
# =============================================================================

def summarize_motion(
    robot,
    start_sec,
    end_sec,
):

    window = robot[
        (robot["plc_time_sec"] >= start_sec)
        & (robot["plc_time_sec"] < end_sec)
    ].copy()

    result = {
        "observations": len(window),

        "joint_path": np.nan,
        "joint_net": np.nan,

        "xy_path": np.nan,
        "xy_net": np.nan,

        "x_range": np.nan,
        "y_range": np.nan,
    }

    if len(window) < 2:
        return result


    # -------------------------------------------------------------------------
    # Joint-position path
    # -------------------------------------------------------------------------

    joint = (
        window[
            JOINT_COLUMNS
        ]
        .astype(float)
    )

    result["joint_path"] = (
        joint
        .diff()
        .abs()
        .sum(axis=1)
        .sum()
    )

    result["joint_net"] = (
        joint.iloc[-1]
        .sub(
            joint.iloc[0]
        )
        .abs()
        .sum()
    )


    # -------------------------------------------------------------------------
    # 2-D ToolX/ToolY path
    # -------------------------------------------------------------------------

    xy = (
        window[
            XY_COLUMNS
        ]
        .dropna()
        .astype(float)
    )

    if len(xy) >= 2:

        xy_diff = (
            xy
            .diff()
        )

        step_distance = np.sqrt(
            (
                xy_diff ** 2
            )
            .sum(axis=1)
        )

        result["xy_path"] = (
            step_distance
            .sum()
        )

        first_xy = (
            xy.iloc[0]
            .to_numpy()
        )

        last_xy = (
            xy.iloc[-1]
            .to_numpy()
        )

        result["xy_net"] = float(
            np.linalg.norm(
                last_xy
                - first_xy
            )
        )

        result["x_range"] = (
            xy["ToolX"].max()
            - xy["ToolX"].min()
        )

        result["y_range"] = (
            xy["ToolY"].max()
            - xy["ToolY"].min()
        )

    return result


# =============================================================================
# 11. ANALYZE ALL FINE-GRAINED WINDOWS
# =============================================================================

rows = []

for _, cycle in central.iterrows():

    for (
        stage,
        start_event,
        end_event,
        process_family,
    ) in PROCESS_WINDOWS:

        duration_sec = (
            cycle[end_event]
            - cycle[start_event]
        ) / EVENT_DIVISOR

        ur3_motion = summarize_motion(
            ur3,
            cycle[
                f"ur3_{start_event}_sec"
            ],
            cycle[
                f"ur3_{end_event}_sec"
            ],
        )

        ur5_motion = summarize_motion(
            ur5,
            cycle[
                f"ur5_{start_event}_sec"
            ],
            cycle[
                f"ur5_{end_event}_sec"
            ],
        )

        row = {
            "cycle_id":
                int(cycle["cycle_id"]),

            "Part Number":
                cycle["Part Number"],

            "Work Fixture":
                cycle["Work Fixture"],

            "stage":
                stage,

            "process_family":
                process_family,

            "duration_sec":
                duration_sec,
        }

        for robot_name, result in [
            ("ur3", ur3_motion),
            ("ur5", ur5_motion),
        ]:

            for metric, value in result.items():

                row[
                    f"{robot_name}_{metric}"
                ] = value

        rows.append(row)


motion = pd.DataFrame(rows)


# =============================================================================
# 12. MOVEMENT RATES
# =============================================================================

for robot_name in [
    "ur3",
    "ur5",
]:

    motion[
        f"{robot_name}_joint_path_per_sec"
    ] = (
        motion[
            f"{robot_name}_joint_path"
        ]
        / motion["duration_sec"]
    )

    motion[
        f"{robot_name}_xy_path_per_sec"
    ] = (
        motion[
            f"{robot_name}_xy_path"
        ]
        / motion["duration_sec"]
    )


# =============================================================================
# 13. COVERAGE
# =============================================================================

print("\n" + "=" * 80)
print("STAGE COVERAGE")
print("=" * 80)

coverage = (
    motion
    .groupby(
        [
            "stage",
            "process_family",
        ],
        sort=False,
    )
    .agg(
        cycles=(
            "cycle_id",
            "count"
        ),

        mean_duration_sec=(
            "duration_sec",
            "mean"
        ),

        ur3_mean_obs=(
            "ur3_observations",
            "mean"
        ),

        ur5_mean_obs=(
            "ur5_observations",
            "mean"
        ),
    )
    .reset_index()
)

print(
    coverage
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 14. JOINT MOTION SIGNATURE
# =============================================================================

print("\n" + "=" * 80)
print("JOINT MOTION SIGNATURE")
print("=" * 80)

joint_signature = (
    motion
    .groupby(
        [
            "stage",
            "process_family",
        ],
        sort=False,
    )
    .agg(
        duration_sec=(
            "duration_sec",
            "mean"
        ),

        ur3_joint_path=(
            "ur3_joint_path",
            "mean"
        ),

        ur5_joint_path=(
            "ur5_joint_path",
            "mean"
        ),

        ur3_joint_rate=(
            "ur3_joint_path_per_sec",
            "mean"
        ),

        ur5_joint_rate=(
            "ur5_joint_path_per_sec",
            "mean"
        ),

        ur3_joint_net=(
            "ur3_joint_net",
            "mean"
        ),

        ur5_joint_net=(
            "ur5_joint_net",
            "mean"
        ),
    )
    .reset_index()
)

joint_signature[
    "joint_rate_difference_ur3_minus_ur5"
] = (
    joint_signature[
        "ur3_joint_rate"
    ]
    - joint_signature[
        "ur5_joint_rate"
    ]
)

print(
    joint_signature
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 15. XY TOOL MOTION SIGNATURE
# =============================================================================

print("\n" + "=" * 80)
print("XY TOOL MOTION SIGNATURE")
print("=" * 80)

xy_signature = (
    motion
    .groupby(
        [
            "stage",
            "process_family",
        ],
        sort=False,
    )
    .agg(
        duration_sec=(
            "duration_sec",
            "mean"
        ),

        ur3_xy_path=(
            "ur3_xy_path",
            "mean"
        ),

        ur5_xy_path=(
            "ur5_xy_path",
            "mean"
        ),

        ur3_xy_rate=(
            "ur3_xy_path_per_sec",
            "mean"
        ),

        ur5_xy_rate=(
            "ur5_xy_path_per_sec",
            "mean"
        ),

        ur3_xy_net=(
            "ur3_xy_net",
            "mean"
        ),

        ur5_xy_net=(
            "ur5_xy_net",
            "mean"
        ),

        ur3_x_range=(
            "ur3_x_range",
            "mean"
        ),

        ur3_y_range=(
            "ur3_y_range",
            "mean"
        ),

        ur5_x_range=(
            "ur5_x_range",
            "mean"
        ),

        ur5_y_range=(
            "ur5_y_range",
            "mean"
        ),
    )
    .reset_index()
)

xy_signature[
    "xy_rate_difference_ur3_minus_ur5"
] = (
    xy_signature[
        "ur3_xy_rate"
    ]
    - xy_signature[
        "ur5_xy_rate"
    ]
)

print(
    xy_signature
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 16. DOMINANT MOTION BY STAGE
# =============================================================================

print("\n" + "=" * 80)
print("DOMINANT MOTION BY STAGE")
print("=" * 80)

dominance_rows = []

for _, row in joint_signature.iterrows():

    stage = row["stage"]

    ur3_joint = row[
        "ur3_joint_rate"
    ]

    ur5_joint = row[
        "ur5_joint_rate"
    ]

    xy_row = xy_signature[
        xy_signature[
            "stage"
        ] == stage
    ].iloc[0]

    ur3_xy = xy_row[
        "ur3_xy_rate"
    ]

    ur5_xy = xy_row[
        "ur5_xy_rate"
    ]

    joint_dominant = (
        "UR3"
        if ur3_joint > ur5_joint
        else "UR5"
        if ur5_joint > ur3_joint
        else "EQUAL"
    )

    xy_dominant = (
        "UR3"
        if ur3_xy > ur5_xy
        else "UR5"
        if ur5_xy > ur3_xy
        else "EQUAL"
    )

    dominance_rows.append({
        "stage":
            stage,

        "process_family":
            row[
                "process_family"
            ],

        "joint_dominant":
            joint_dominant,

        "xy_dominant":
            xy_dominant,

        "ur3_joint_rate":
            ur3_joint,

        "ur5_joint_rate":
            ur5_joint,

        "ur3_xy_rate":
            ur3_xy,

        "ur5_xy_rate":
            ur5_xy,
    })


dominance = pd.DataFrame(
    dominance_rows
)

print(
    dominance
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 17. TASK SIGNATURE BY FIXTURE
# =============================================================================

print("\n" + "=" * 80)
print("TASK-ACTION SIGNATURE BY FIXTURE")
print("=" * 80)

task = motion[
    motion["stage"] == "t7_t8"
].copy()

task_fixture = (
    task
    .groupby(
        "Work Fixture"
    )
    .agg(
        parts=(
            "Part Number",
            "count"
        ),

        duration_sec=(
            "duration_sec",
            "mean"
        ),

        ur3_joint_rate=(
            "ur3_joint_path_per_sec",
            "mean"
        ),

        ur5_joint_rate=(
            "ur5_joint_path_per_sec",
            "mean"
        ),

        ur3_xy_rate=(
            "ur3_xy_path_per_sec",
            "mean"
        ),

        ur5_xy_rate=(
            "ur5_xy_path_per_sec",
            "mean"
        ),

        ur3_xy_path=(
            "ur3_xy_path",
            "mean"
        ),

        ur5_xy_path=(
            "ur5_xy_path",
            "mean"
        ),
    )
    .reset_index()
)

print(
    task_fixture
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 18. MOTION CONCENTRATION BY ROBOT
# =============================================================================

print("\n" + "=" * 80)
print("MOTION CONCENTRATION BY ROBOT")
print("=" * 80)

for robot_name in [
    "ur3",
    "ur5",
]:

    stage_motion = (
        motion
        .groupby(
            [
                "stage",
                "process_family",
            ],
            sort=False,
        )[
            f"{robot_name}_joint_path"
        ]
        .mean()
        .reset_index()
    )

    total = (
        stage_motion[
            f"{robot_name}_joint_path"
        ]
        .sum()
    )

    stage_motion[
        "share_of_selected_motion_pct"
    ] = (
        stage_motion[
            f"{robot_name}_joint_path"
        ]
        / total
        * 100
    )

    print(
        f"\n{robot_name.upper()}"
    )

    print(
        stage_motion
        .sort_values(
            "share_of_selected_motion_pct",
            ascending=False,
        )
        .round(4)
        .to_string(index=False)
    )


# =============================================================================
# 19. SAVE
# =============================================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

motion.to_csv(
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
    f"{motion.shape}"
)


# =============================================================================
# 20. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
This analysis compares UR3 and UR5 physical-motion signatures across
fine-grained process stages.

ToolZ is unavailable in the PLC datasets, so ToolX and ToolY are used
explicitly as a two-dimensional XY movement indicator. No 3-D TCP
distance is claimed.

Joint-position path and XY tool path provide two independent views of
physical motion.

Because the cell is pipelined, movement occurring during a part's
process stage can belong to work being performed for another part.
Therefore stage-level dominance is evidence of temporal movement
concentration, not automatic proof of task ownership.

The strongest role interpretation should come from a repeated pattern
across pre-task, task, post-task, input-handling and output-handling
stages rather than from a single window.
"""
)