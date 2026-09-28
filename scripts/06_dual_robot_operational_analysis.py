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

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

UR3_OUTPUT = OUTPUT_DIR / "ur3_operational_features.csv"
UR5_OUTPUT = OUTPUT_DIR / "ur5_operational_features.csv"


# =============================================================================
# 2. LOAD ROBOT TELEMETRY
# =============================================================================

ur3 = pd.read_csv(UR3_FILE)
ur5 = pd.read_csv(UR5_FILE)

print("=" * 80)
print("NIST DUAL-ROBOT OPERATIONAL ANALYSIS")
print("=" * 80)

print(f"\nUR3 rows: {len(ur3):,}")
print(f"UR5 rows: {len(ur5):,}")


# =============================================================================
# 3. COMMON ROBOT SIGNALS
# =============================================================================

velocity_columns = [
    "j1_qdactual",
    "j2_qdactual",
    "j3_qdactual",
    "j4_qdactual",
    "j5_qdactual",
    "j6_qdactual",
]

position_columns = [
    "j1_qactual",
    "j2_qactual",
    "j3_qactual",
    "j4_qactual",
    "j5_qactual",
    "j6_qactual",
]


# =============================================================================
# 4. VALIDATE REQUIRED SIGNALS
# =============================================================================

print("\n" + "=" * 80)
print("SIGNAL VALIDATION")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    missing_velocity = [
        column
        for column in velocity_columns
        if column not in robot.columns
    ]

    missing_position = [
        column
        for column in position_columns
        if column not in robot.columns
    ]

    print(f"\n{robot_name}")

    print(
        f"Velocity signals present: "
        f"{len(velocity_columns) - len(missing_velocity)} "
        f"of {len(velocity_columns)}"
    )

    print(
        f"Position signals present: "
        f"{len(position_columns) - len(missing_position)} "
        f"of {len(position_columns)}"
    )

    if missing_velocity or missing_position:
        raise ValueError(
            f"{robot_name} required joint signals missing."
        )


# =============================================================================
# 5. TIME NORMALIZATION
# =============================================================================

# NIST documentation indicates PLC time should be divided by 10^7.

for robot in [ur3, ur5]:

    robot["plc_time_sec"] = (
        robot["PLCTime"] / 1e7
    )

    robot["elapsed_sec"] = (
        robot["plc_time_sec"]
        - robot["plc_time_sec"].iloc[0]
    )


# =============================================================================
# 6. DERIVE TRANSPARENT MOVEMENT FEATURES
# =============================================================================

def add_robot_features(robot):

    abs_velocity = robot[
        velocity_columns
    ].abs()

    robot["joint_speed_abs_mean"] = (
        abs_velocity.mean(axis=1)
    )

    robot["joint_speed_abs_max"] = (
        abs_velocity.max(axis=1)
    )

    robot["joint_speed_abs_sum"] = (
        abs_velocity.sum(axis=1)
    )

    robot["moving_joint_count"] = (
        abs_velocity > 0
    ).sum(axis=1)

    return robot


ur3 = add_robot_features(ur3)
ur5 = add_robot_features(ur5)


# =============================================================================
# 7. EXACT-ZERO MOVEMENT AUDIT
# =============================================================================

# This section deliberately uses exact zeros only.
#
# It is NOT yet an idle/moving classifier.
# It simply establishes how frequently the recorded telemetry contains
# exactly zero velocity across all six joints.

print("\n" + "=" * 80)
print("EXACT-ZERO VELOCITY AUDIT")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    all_zero = (
        robot[velocity_columns] == 0
    ).all(axis=1)

    any_nonzero = ~all_zero

    print(f"\n{robot_name}")

    print(
        f"All 6 joint velocities exactly zero: "
        f"{all_zero.sum():,} "
        f"({all_zero.mean() * 100:.2f}%)"
    )

    print(
        f"At least 1 joint velocity non-zero:  "
        f"{any_nonzero.sum():,} "
        f"({any_nonzero.mean() * 100:.2f}%)"
    )


# =============================================================================
# 8. JOINT-SPEED DISTRIBUTIONS
# =============================================================================

print("\n" + "=" * 80)
print("MEAN ABSOLUTE JOINT-SPEED DISTRIBUTION")
print("=" * 80)

percentiles = [
    0.00,
    0.01,
    0.05,
    0.10,
    0.25,
    0.50,
    0.75,
    0.90,
    0.95,
    0.99,
    1.00,
]

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    print(f"\n{robot_name}")

    quantiles = (
        robot["joint_speed_abs_mean"]
        .quantile(percentiles)
    )

    for percentile, value in quantiles.items():

        print(
            f"{percentile * 100:>6.1f}%  "
            f"{value:.8f}"
        )


# =============================================================================
# 9. MAXIMUM JOINT-SPEED DISTRIBUTION
# =============================================================================

print("\n" + "=" * 80)
print("MAX ABSOLUTE JOINT-SPEED DISTRIBUTION")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    print(f"\n{robot_name}")

    quantiles = (
        robot["joint_speed_abs_max"]
        .quantile(percentiles)
    )

    for percentile, value in quantiles.items():

        print(
            f"{percentile * 100:>6.1f}%  "
            f"{value:.8f}"
        )


# =============================================================================
# 10. INDIVIDUAL JOINT ACTIVITY
# =============================================================================

print("\n" + "=" * 80)
print("INDIVIDUAL JOINT VELOCITY SUMMARY")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    print(f"\n{robot_name}")

    summary_rows = []

    for column in velocity_columns:

        absolute = robot[column].abs()

        summary_rows.append({
            "joint": column,
            "mean_abs_speed": absolute.mean(),
            "median_abs_speed": absolute.median(),
            "p95_abs_speed": absolute.quantile(0.95),
            "max_abs_speed": absolute.max(),
            "exact_zero_pct":
                (absolute == 0).mean() * 100,
        })

    summary = pd.DataFrame(summary_rows)

    print(
        summary
        .round(6)
        .to_string(index=False)
    )


# =============================================================================
# 11. NUMBER OF MOVING JOINTS
# =============================================================================

print("\n" + "=" * 80)
print("NON-ZERO JOINT COUNT DISTRIBUTION")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    counts = (
        robot["moving_joint_count"]
        .value_counts()
        .sort_index()
    )

    print(f"\n{robot_name}")

    for joint_count, count in counts.items():

        percentage = (
            count / len(robot)
        ) * 100

        print(
            f"{joint_count} non-zero joints: "
            f"{count:>7,} "
            f"({percentage:>6.2f}%)"
        )


# =============================================================================
# 12. TELEMETRY COVERAGE
# =============================================================================

print("\n" + "=" * 80)
print("TELEMETRY COVERAGE")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    print(f"\n{robot_name}")

    print(
        f"Start:    "
        f"{robot['plc_time_sec'].iloc[0]:.6f} sec"
    )

    print(
        f"End:      "
        f"{robot['plc_time_sec'].iloc[-1]:.6f} sec"
    )

    print(
        f"Duration: "
        f"{robot['elapsed_sec'].iloc[-1]:.6f} sec"
    )


# =============================================================================
# 13. COMPARE UR3 AND UR5 ACTIVITY DISTRIBUTIONS
# =============================================================================

print("\n" + "=" * 80)
print("UR3 vs UR5 ACTIVITY COMPARISON")
print("=" * 80)

comparison = pd.DataFrame({
    "robot": ["UR3", "UR5"],

    "mean_abs_joint_speed": [
        ur3["joint_speed_abs_mean"].mean(),
        ur5["joint_speed_abs_mean"].mean(),
    ],

    "median_abs_joint_speed": [
        ur3["joint_speed_abs_mean"].median(),
        ur5["joint_speed_abs_mean"].median(),
    ],

    "p95_abs_joint_speed": [
        ur3["joint_speed_abs_mean"].quantile(0.95),
        ur5["joint_speed_abs_mean"].quantile(0.95),
    ],

    "mean_max_joint_speed": [
        ur3["joint_speed_abs_max"].mean(),
        ur5["joint_speed_abs_max"].mean(),
    ],
})

print(
    comparison
    .round(6)
    .to_string(index=False)
)


# =============================================================================
# 14. ROBOTTIME AUDIT
# =============================================================================

# We do not use RobotTime for alignment yet.
# First inspect its progression and relationship with PLCTime.

print("\n" + "=" * 80)
print("ROBOTTIME AUDIT")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    print(f"\n{robot_name}")

    print(
        f"RobotTime first: "
        f"{robot['RobotTime'].iloc[0]}"
    )

    print(
        f"RobotTime last:  "
        f"{robot['RobotTime'].iloc[-1]}"
    )

    print(
        f"RobotTime min:   "
        f"{robot['RobotTime'].min()}"
    )

    print(
        f"RobotTime max:   "
        f"{robot['RobotTime'].max()}"
    )

    print(
        f"RobotTime missing: "
        f"{robot['RobotTime'].isna().sum():,}"
    )

    robot_time_diff = (
        robot["RobotTime"]
        .diff()
        .dropna()
    )

    print(
        f"RobotTime non-positive differences: "
        f"{(robot_time_diff <= 0).sum():,}"
    )


# =============================================================================
# 15. SAVE FEATURE-ENRICHED ROBOT DATA
# =============================================================================

output_columns = [
    "PLCTime",
    "RobotTime",
    "plc_time_sec",
    "elapsed_sec",
] + position_columns + velocity_columns + [
    "joint_speed_abs_mean",
    "joint_speed_abs_max",
    "joint_speed_abs_sum",
    "moving_joint_count",
]

ur3_output = ur3[output_columns].copy()
ur5_output = ur5[output_columns].copy()

ur3_output.to_csv(
    UR3_OUTPUT,
    index=False
)

ur5_output.to_csv(
    UR5_OUTPUT,
    index=False
)

print("\n" + "=" * 80)
print("OUTPUT")
print("=" * 80)

print(f"\nUR3 features:")
print(UR3_OUTPUT)

print(f"\nUR5 features:")
print(UR5_OUTPUT)

print(
    f"\nUR3 output shape: "
    f"{ur3_output.shape}"
)

print(
    f"UR5 output shape: "
    f"{ur5_output.shape}"
)


# =============================================================================
# 16. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
This script characterises UR3 and UR5 physical activity using the same
six joint-velocity signals.

No arbitrary velocity threshold has yet been used to classify robot
states as moving or idle.

Exact-zero velocity is reported only as an observed telemetry condition,
not as proof of operational idle time.

The next step is to use the observed velocity distributions together
with the established clock alignment to map robot activity into the
NIST t1-t14 process windows.

That process-level alignment is required before interpreting waiting
time as robot idle time, resource contention, synchronization delay,
or another operational condition.
"""
)