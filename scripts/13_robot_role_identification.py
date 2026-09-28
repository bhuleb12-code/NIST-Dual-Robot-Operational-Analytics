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
    / "robot_role_identification.csv"
)


# =============================================================================
# 2. CONSTANTS
# =============================================================================

ROBOT_PLC_DIVISOR = 1e6
EVENT_DIVISOR = 1e7

CENTRAL_START = 6
CENTRAL_END = 55


# =============================================================================
# 3. PROCESS WINDOWS
# =============================================================================

# These windows correspond to operational sections of the documented
# PartData process timeline.
#
# IMPORTANT:
# Their process meaning is known, but robot ownership is NOT assumed.

PROCESS_WINDOWS = [
    (
        "input_handling",
        "PickFromInputAssigned",
        "PlaceInWFComplete",
    ),
    (
        "pre_task_transition",
        "PlaceInWFComplete",
        "TaskActionStart",
    ),
    (
        "task_action",
        "TaskActionStart",
        "TaskActionComplete",
    ),
    (
        "post_task_transition",
        "TaskActionComplete",
        "PickFromWFAssigned",
    ),
    (
        "output_handling",
        "PickFromWFAssigned",
        "PlaceInOutputComplete",
    ),
]


# =============================================================================
# 4. LOAD DATA
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
print("NIST ROBOTIC WORK CELL - ROBOT ROLE IDENTIFICATION")
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

print("\n" + "=" * 80)
print("ROBOT CLOCK RANGES")
print("=" * 80)

print(
    f"\nUR3: "
    f"{ur3['plc_time_sec'].min():.6f} -> "
    f"{ur3['plc_time_sec'].max():.6f}"
)

print(
    f"UR5: "
    f"{ur5['plc_time_sec'].min():.6f} -> "
    f"{ur5['plc_time_sec'].max():.6f}"
)


# =============================================================================
# 6. AVAILABLE PHYSICAL SIGNALS
# =============================================================================

joint_position_columns = [
    "j1_qactual",
    "j2_qactual",
    "j3_qactual",
    "j4_qactual",
    "j5_qactual",
    "j6_qactual",
]

tcp_columns = [
    "ToolX",
    "ToolY",
    "ToolZ",
]

print("\n" + "=" * 80)
print("PHYSICAL SIGNAL AVAILABILITY")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    print(f"\n{robot_name}")

    for column in (
        joint_position_columns
        + tcp_columns
    ):

        if column not in robot.columns:

            print(
                f"{column:<15} MISSING COLUMN"
            )

            continue

        non_null = (
            robot[column]
            .notna()
            .sum()
        )

        unique = (
            robot[column]
            .nunique(
                dropna=True
            )
        )

        print(
            f"{column:<15} "
            f"non-null={non_null:>6,} "
            f"unique={unique:>6,}"
        )


# =============================================================================
# 7. CYCLE-SPECIFIC ROBOT CLOCK ANCHORS
# =============================================================================

part["ur3_anchor_sec"] = (
    part["UR3TimePartAdded"]
    / 1e6
)

part["ur5_anchor_sec"] = (
    part["UR5TimePartAdded"]
    / 1e6
)


required_event_columns = set()

for _, start_event, end_event in PROCESS_WINDOWS:

    required_event_columns.add(
        start_event
    )

    required_event_columns.add(
        end_event
    )


for event_column in sorted(
    required_event_columns
):

    offset_sec = (
        part[event_column]
        - part["PartAdded"]
    ) / EVENT_DIVISOR

    part[
        f"{event_column}_offset_sec"
    ] = offset_sec

    part[
        f"ur3_{event_column}_sec"
    ] = (
        part["ur3_anchor_sec"]
        + offset_sec
    )

    part[
        f"ur5_{event_column}_sec"
    ] = (
        part["ur5_anchor_sec"]
        + offset_sec
    )


# =============================================================================
# 8. CENTRAL PRODUCTION WINDOW
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
    f"\nCentral production parts: "
    f"{CENTRAL_START}-{CENTRAL_END}"
)

print(
    f"Parts included: "
    f"{len(central)}"
)


# =============================================================================
# 9. PHYSICAL-MOVEMENT FUNCTION
# =============================================================================

def summarize_physical_movement(
    robot,
    start_sec,
    end_sec,
):
    """
    Summarize actual robot displacement within one process window.

    Joint path:
        Sum of absolute sample-to-sample changes across all six qactual
        signals.

    Joint net displacement:
        Absolute difference between first and last observed joint positions.

    TCP path:
        Sum of Euclidean ToolX/ToolY/ToolZ sample-to-sample displacement,
        only when all three TCP columns contain usable data.

    TCP net displacement:
        Euclidean distance between first and last TCP observation.

    These are descriptive movement indicators and are not automatically
    interpreted as task ownership.
    """

    window = robot[
        (robot["plc_time_sec"] >= start_sec)
        & (robot["plc_time_sec"] < end_sec)
    ].copy()

    result = {
        "observations": len(window),
        "joint_path": np.nan,
        "joint_net_displacement": np.nan,
        "tcp_path": np.nan,
        "tcp_net_displacement": np.nan,
    }

    if len(window) < 2:
        return result


    # -------------------------------------------------------------------------
    # Joint-position movement
    # -------------------------------------------------------------------------

    available_joint_columns = [
        column
        for column in joint_position_columns
        if (
            column in window.columns
            and window[column].notna().sum() >= 2
        )
    ]

    if available_joint_columns:

        joint_data = (
            window[
                available_joint_columns
            ]
            .astype(float)
        )

        joint_diffs = (
            joint_data
            .diff()
            .abs()
        )

        result["joint_path"] = (
            joint_diffs
            .sum(axis=1)
            .sum()
        )

        first_joint = (
            joint_data.iloc[0]
        )

        last_joint = (
            joint_data.iloc[-1]
        )

        result[
            "joint_net_displacement"
        ] = (
            last_joint
            .sub(first_joint)
            .abs()
            .sum()
        )


    # -------------------------------------------------------------------------
    # TCP movement
    # -------------------------------------------------------------------------

    tcp_usable = (
        all(
            column in window.columns
            for column in tcp_columns
        )
        and
        all(
            window[column]
            .notna()
            .sum() >= 2
            for column in tcp_columns
        )
    )

    if tcp_usable:

        tcp_data = (
            window[tcp_columns]
            .dropna()
            .astype(float)
        )

        if len(tcp_data) >= 2:

            tcp_diff = (
                tcp_data
                .diff()
            )

            tcp_step_distance = np.sqrt(
                (
                    tcp_diff ** 2
                )
                .sum(axis=1)
            )

            result["tcp_path"] = (
                tcp_step_distance
                .sum()
            )

            first_tcp = (
                tcp_data.iloc[0]
                .to_numpy()
            )

            last_tcp = (
                tcp_data.iloc[-1]
                .to_numpy()
            )

            result[
                "tcp_net_displacement"
            ] = float(
                np.linalg.norm(
                    last_tcp
                    - first_tcp
                )
            )

    return result


# =============================================================================
# 10. ANALYZE BOTH ROBOTS ACROSS PROCESS WINDOWS
# =============================================================================

rows = []

for _, cycle in central.iterrows():

    for (
        process_window,
        start_event,
        end_event,
    ) in PROCESS_WINDOWS:

        duration_sec = (
            (
                cycle[end_event]
                - cycle[start_event]
            )
            / EVENT_DIVISOR
        )

        ur3_summary = (
            summarize_physical_movement(
                ur3,
                cycle[
                    f"ur3_{start_event}_sec"
                ],
                cycle[
                    f"ur3_{end_event}_sec"
                ],
            )
        )

        ur5_summary = (
            summarize_physical_movement(
                ur5,
                cycle[
                    f"ur5_{start_event}_sec"
                ],
                cycle[
                    f"ur5_{end_event}_sec"
                ],
            )
        )

        rows.append({
            "cycle_id":
                int(cycle["cycle_id"]),

            "Part Number":
                cycle["Part Number"],

            "Work Fixture":
                cycle["Work Fixture"],

            "process_window":
                process_window,

            "duration_sec":
                duration_sec,

            "ur3_observations":
                ur3_summary[
                    "observations"
                ],

            "ur3_joint_path":
                ur3_summary[
                    "joint_path"
                ],

            "ur3_joint_net_displacement":
                ur3_summary[
                    "joint_net_displacement"
                ],

            "ur3_tcp_path":
                ur3_summary[
                    "tcp_path"
                ],

            "ur3_tcp_net_displacement":
                ur3_summary[
                    "tcp_net_displacement"
                ],

            "ur5_observations":
                ur5_summary[
                    "observations"
                ],

            "ur5_joint_path":
                ur5_summary[
                    "joint_path"
                ],

            "ur5_joint_net_displacement":
                ur5_summary[
                    "joint_net_displacement"
                ],

            "ur5_tcp_path":
                ur5_summary[
                    "tcp_path"
                ],

            "ur5_tcp_net_displacement":
                ur5_summary[
                    "tcp_net_displacement"
                ],
        })


movement = pd.DataFrame(
    rows
)


# =============================================================================
# 11. COVERAGE
# =============================================================================

print("\n" + "=" * 80)
print("PROCESS-WINDOW COVERAGE")
print("=" * 80)

coverage = (
    movement
    .groupby(
        "process_window",
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
    coverage
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 12. JOINT-POSITION MOVEMENT PROFILE
# =============================================================================

print("\n" + "=" * 80)
print("JOINT-POSITION MOVEMENT PROFILE")
print("=" * 80)

joint_profile = (
    movement
    .groupby(
        "process_window",
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

        ur3_mean_joint_path=(
            "ur3_joint_path",
            "mean"
        ),

        ur5_mean_joint_path=(
            "ur5_joint_path",
            "mean"
        ),

        ur3_mean_net_displacement=(
            "ur3_joint_net_displacement",
            "mean"
        ),

        ur5_mean_net_displacement=(
            "ur5_joint_net_displacement",
            "mean"
        ),
    )
    .reset_index()
)

joint_profile[
    "ur3_minus_ur5_joint_path"
] = (
    joint_profile[
        "ur3_mean_joint_path"
    ]
    - joint_profile[
        "ur5_mean_joint_path"
    ]
)

print(
    joint_profile
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 13. MOVEMENT RATE
# =============================================================================

# Path is naturally larger in longer windows.
# Divide by duration so that windows can also be compared by movement rate.

movement["ur3_joint_path_per_sec"] = (
    movement["ur3_joint_path"]
    / movement["duration_sec"]
)

movement["ur5_joint_path_per_sec"] = (
    movement["ur5_joint_path"]
    / movement["duration_sec"]
)

print("\n" + "=" * 80)
print("JOINT-PATH RATE BY PROCESS WINDOW")
print("=" * 80)

rate_profile = (
    movement
    .groupby(
        "process_window",
        sort=False,
    )
    .agg(
        ur3_joint_path_per_sec=(
            "ur3_joint_path_per_sec",
            "mean"
        ),

        ur5_joint_path_per_sec=(
            "ur5_joint_path_per_sec",
            "mean"
        ),
    )
    .reset_index()
)

rate_profile[
    "ur3_minus_ur5_rate"
] = (
    rate_profile[
        "ur3_joint_path_per_sec"
    ]
    - rate_profile[
        "ur5_joint_path_per_sec"
    ]
)

print(
    rate_profile
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 14. TCP MOVEMENT PROFILE
# =============================================================================

print("\n" + "=" * 80)
print("TCP MOVEMENT PROFILE")
print("=" * 80)

tcp_profile = (
    movement
    .groupby(
        "process_window",
        sort=False,
    )
    .agg(
        ur3_cycles_with_tcp=(
            "ur3_tcp_path",
            "count"
        ),

        ur5_cycles_with_tcp=(
            "ur5_tcp_path",
            "count"
        ),

        ur3_mean_tcp_path=(
            "ur3_tcp_path",
            "mean"
        ),

        ur5_mean_tcp_path=(
            "ur5_tcp_path",
            "mean"
        ),

        ur3_mean_tcp_net_displacement=(
            "ur3_tcp_net_displacement",
            "mean"
        ),

        ur5_mean_tcp_net_displacement=(
            "ur5_tcp_net_displacement",
            "mean"
        ),
    )
    .reset_index()
)

print(
    tcp_profile
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 15. TASK-ACTION PROFILE BY FIXTURE
# =============================================================================

print("\n" + "=" * 80)
print("TASK-ACTION MOVEMENT BY WORK FIXTURE")
print("=" * 80)

task_action = movement[
    movement[
        "process_window"
    ] == "task_action"
].copy()

task_fixture = (
    task_action
    .groupby(
        "Work Fixture"
    )
    .agg(
        parts=(
            "Part Number",
            "count"
        ),

        mean_duration_sec=(
            "duration_sec",
            "mean"
        ),

        ur3_mean_joint_path=(
            "ur3_joint_path",
            "mean"
        ),

        ur5_mean_joint_path=(
            "ur5_joint_path",
            "mean"
        ),

        ur3_mean_joint_path_per_sec=(
            "ur3_joint_path_per_sec",
            "mean"
        ),

        ur5_mean_joint_path_per_sec=(
            "ur5_joint_path_per_sec",
            "mean"
        ),

        ur3_mean_tcp_path=(
            "ur3_tcp_path",
            "mean"
        ),

        ur5_mean_tcp_path=(
            "ur5_tcp_path",
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
# 16. INPUT vs TASK vs OUTPUT CONTRAST
# =============================================================================

print("\n" + "=" * 80)
print("ROBOT ROLE CONTRAST")
print("=" * 80)

contrast_windows = [
    "input_handling",
    "task_action",
    "output_handling",
]

contrast = rate_profile[
    rate_profile[
        "process_window"
    ].isin(
        contrast_windows
    )
].copy()

print(
    contrast
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 17. SIMPLE EMPIRICAL ROLE SIGNAL
# =============================================================================

# This does NOT automatically assign robot roles.
#
# It simply reports which robot has the larger actual joint-position
# path rate in each major operational window.

print("\n" + "=" * 80)
print("DOMINANT MOVEMENT SIGNAL")
print("=" * 80)

for _, row in contrast.iterrows():

    ur3_rate = (
        row[
            "ur3_joint_path_per_sec"
        ]
    )

    ur5_rate = (
        row[
            "ur5_joint_path_per_sec"
        ]
    )

    if (
        pd.isna(ur3_rate)
        or pd.isna(ur5_rate)
    ):
        dominant = "UNRESOLVED"

    elif ur3_rate > ur5_rate:
        dominant = "UR3"

    elif ur5_rate > ur3_rate:
        dominant = "UR5"

    else:
        dominant = "EQUAL"

    print(
        f"\n{row['process_window']}:"
    )

    print(
        f"  UR3 joint-path rate: "
        f"{ur3_rate:.4f}"
    )

    print(
        f"  UR5 joint-path rate: "
        f"{ur5_rate:.4f}"
    )

    print(
        f"  Larger movement signal: "
        f"{dominant}"
    )


# =============================================================================
# 18. SAVE
# =============================================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

movement.to_csv(
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
    f"{movement.shape}"
)


# =============================================================================
# 19. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
This analysis uses actual joint-position displacement as the primary
physical-movement indicator.

This avoids relying solely on qdactual because earlier reconnaissance
identified persistent non-zero velocity behaviour in some joints.

The process windows have known meanings from the PartData timeline,
but robot ownership is not assumed in advance.

A larger movement signal within a process window is evidence that a
robot is physically more active during that interval. It is not, by
itself, sufficient to prove exclusive ownership of the process action
because the work cell is pipelined and robots can simultaneously serve
different parts.

Robot-role identification should therefore rely on the complete pattern
across input handling, task action, output handling, fixture behaviour
and available TCP movement rather than a single statistic.
"""
)