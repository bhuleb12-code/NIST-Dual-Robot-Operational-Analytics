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

PARTDATA_FILE = (
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


# =============================================================================
# 2. LOAD DATA
# =============================================================================

part = pd.read_csv(PARTDATA_FILE)
ur3 = pd.read_csv(UR3_FILE)
ur5 = pd.read_csv(UR5_FILE)

print("=" * 80)
print("NIST TELEMETRY - PROCESS COVERAGE AUDIT")
print("=" * 80)

print(f"\nPartData rows: {len(part):,}")
print(f"UR3 rows:      {len(ur3):,}")
print(f"UR5 rows:      {len(ur5):,}")


# =============================================================================
# 3. NORMALIZE DOCUMENTED CLOCKS
# =============================================================================

# PartData robot timestamps:
# NIST documentation -> divide by 10^6.

part["ur3_part_added_sec"] = (
    part["UR3TimePartAdded"] / 1e6
)

part["ur5_part_added_sec"] = (
    part["UR5TimePartAdded"] / 1e6
)

# Robot telemetry PLCTime:
# NIST documentation -> divide by 10^7.

ur3["plc_time_sec"] = (
    ur3["PLCTime"] / 1e7
)

ur5["plc_time_sec"] = (
    ur5["PLCTime"] / 1e7
)


# =============================================================================
# 4. TELEMETRY WINDOWS
# =============================================================================

ur3_start = ur3["plc_time_sec"].iloc[0]
ur3_end = ur3["plc_time_sec"].iloc[-1]

ur5_start = ur5["plc_time_sec"].iloc[0]
ur5_end = ur5["plc_time_sec"].iloc[-1]

ur3_duration = ur3_end - ur3_start
ur5_duration = ur5_end - ur5_start

print("\n" + "=" * 80)
print("TELEMETRY WINDOWS")
print("=" * 80)

print(
    f"\nUR3: {ur3_start:.6f} -> "
    f"{ur3_end:.6f} sec "
    f"(duration {ur3_duration:.6f} sec)"
)

print(
    f"UR5: {ur5_start:.6f} -> "
    f"{ur5_end:.6f} sec "
    f"(duration {ur5_duration:.6f} sec)"
)


# =============================================================================
# 5. DUAL-ROBOT COMMON WINDOW
# =============================================================================

common_start = max(
    ur3_start,
    ur5_start
)

common_end = min(
    ur3_end,
    ur5_end
)

common_duration = (
    common_end - common_start
)

print("\n" + "=" * 80)
print("COMMON UR3 / UR5 TELEMETRY WINDOW")
print("=" * 80)

print(f"\nStart:    {common_start:.6f} sec")
print(f"End:      {common_end:.6f} sec")
print(f"Duration: {common_duration:.6f} sec")


# =============================================================================
# 6. PARTDATA ROBOT CLOCK RANGES
# =============================================================================

print("\n" + "=" * 80)
print("PARTDATA ROBOT CLOCK RANGES")
print("=" * 80)

print(
    f"\nUR3TimePartAdded: "
    f"{part['ur3_part_added_sec'].min():.6f} -> "
    f"{part['ur3_part_added_sec'].max():.6f}"
)

print(
    f"UR5TimePartAdded: "
    f"{part['ur5_part_added_sec'].min():.6f} -> "
    f"{part['ur5_part_added_sec'].max():.6f}"
)


# =============================================================================
# 7. PART-TO-PART INTERVAL SIGNATURE
# =============================================================================

part["ur3_interval_sec"] = (
    part["ur3_part_added_sec"].diff()
)

part["ur5_interval_sec"] = (
    part["ur5_part_added_sec"].diff()
)

print("\n" + "=" * 80)
print("PART ARRIVAL SEQUENCE")
print("=" * 80)

arrival_table = part[
    [
        "cycle_id",
        "Part Number",
        "Work Fixture",
        "ur3_part_added_sec",
        "ur5_part_added_sec",
        "ur3_interval_sec",
        "ur5_interval_sec",
    ]
].copy()

print(
    arrival_table
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 8. SEARCH FOR ~273-SECOND PART WINDOWS
# =============================================================================

# The robot telemetry capture is approximately 273 seconds long.
# Here we identify every consecutive group of PartData arrivals whose
# first-to-last span fits inside that duration.
#
# This does NOT yet assert that any one group is the telemetry match.

print("\n" + "=" * 80)
print("CONSECUTIVE PART GROUPS WITHIN TELEMETRY DURATION")
print("=" * 80)

candidate_groups = []

for start_idx in range(len(part)):

    start_time = part.loc[
        start_idx,
        "ur3_part_added_sec"
    ]

    included_indices = []

    for end_idx in range(
        start_idx,
        len(part)
    ):

        end_time = part.loc[
            end_idx,
            "ur3_part_added_sec"
        ]

        span = end_time - start_time

        if span <= common_duration:
            included_indices.append(end_idx)
        else:
            break

    if included_indices:

        final_idx = included_indices[-1]

        span = (
            part.loc[
                final_idx,
                "ur3_part_added_sec"
            ]
            - start_time
        )

        candidate_groups.append({
            "start_cycle":
                int(part.loc[start_idx, "cycle_id"]),

            "end_cycle":
                int(part.loc[final_idx, "cycle_id"]),

            "parts":
                final_idx - start_idx + 1,

            "arrival_span_sec":
                span,

            "unused_window_sec":
                common_duration - span,
        })


candidate_df = pd.DataFrame(
    candidate_groups
)

print(
    candidate_df
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 9. PART COUNTS EXPECTED FROM OBSERVED ARRIVAL RATE
# =============================================================================

print("\n" + "=" * 80)
print("EXPECTED PART ARRIVALS DURING TELEMETRY CAPTURE")
print("=" * 80)

median_interval = (
    part["ur3_interval_sec"]
    .dropna()
    .median()
)

mean_interval = (
    part["ur3_interval_sec"]
    .dropna()
    .mean()
)

print(
    f"\nMedian PartData arrival interval: "
    f"{median_interval:.4f} sec"
)

print(
    f"Mean PartData arrival interval:   "
    f"{mean_interval:.4f} sec"
)

print(
    f"\nCommon telemetry duration: "
    f"{common_duration:.4f} sec"
)

print(
    f"Duration / median interval: "
    f"{common_duration / median_interval:.2f}"
)

print(
    f"Duration / mean interval:   "
    f"{common_duration / mean_interval:.2f}"
)


# =============================================================================
# 10. ROBOT POSITION CHANGE SIGNATURE
# =============================================================================

position_columns = [
    "j1_qactual",
    "j2_qactual",
    "j3_qactual",
    "j4_qactual",
    "j5_qactual",
    "j6_qactual",
]

print("\n" + "=" * 80)
print("TELEMETRY POSITION-CHANGE SIGNATURE")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    change = (
        robot[position_columns]
        .diff()
        .abs()
        .sum(axis=1)
    )

    print(f"\n{robot_name}")

    print(
        f"Median summed position change/sample: "
        f"{change.median():.8f}"
    )

    print(
        f"95th percentile:                      "
        f"{change.quantile(0.95):.8f}"
    )

    print(
        f"Maximum:                              "
        f"{change.max():.8f}"
    )


# =============================================================================
# 11. TELEMETRY BLOCK STRUCTURE
# =============================================================================

# Summarize the robot capture in 10-second blocks.
# This gives us an activity fingerprint without yet imposing an
# idle/moving classification threshold.

print("\n" + "=" * 80)
print("10-SECOND TELEMETRY ACTIVITY BLOCKS")
print("=" * 80)


def block_summary(robot, robot_name):

    data = robot.copy()

    data["elapsed_sec"] = (
        data["plc_time_sec"]
        - data["plc_time_sec"].iloc[0]
    )

    data["block_10s"] = (
        data["elapsed_sec"] // 10
    ).astype(int)

    data["position_change"] = (
        data[position_columns]
        .diff()
        .abs()
        .sum(axis=1)
    )

    summary = (
        data.groupby("block_10s")
        .agg(
            observations=("PLCTime", "size"),
            mean_position_change=(
                "position_change",
                "mean"
            ),
            median_position_change=(
                "position_change",
                "median"
            ),
            max_position_change=(
                "position_change",
                "max"
            ),
        )
        .reset_index()
    )

    summary["start_sec"] = (
        summary["block_10s"] * 10
    )

    summary["end_sec"] = (
        summary["start_sec"] + 10
    )

    print(f"\n{robot_name}")

    print(
        summary[
            [
                "start_sec",
                "end_sec",
                "observations",
                "mean_position_change",
                "median_position_change",
                "max_position_change",
            ]
        ]
        .round(6)
        .to_string(index=False)
    )


block_summary(
    ur3,
    "UR3"
)

block_summary(
    ur5,
    "UR5"
)


# =============================================================================
# 12. TEST POSSIBLE CLOCK SCALE RELATIONSHIP
# =============================================================================

print("\n" + "=" * 80)
print("PARTDATA ROBOT CLOCK vs TELEMETRY PLC CLOCK")
print("=" * 80)

# The absolute values differ by roughly a factor of ten.
# We report this relationship but do not assume equivalence.

ur3_ratio_start = (
    part["ur3_part_added_sec"].iloc[0]
    / ur3_start
)

ur5_ratio_start = (
    part["ur5_part_added_sec"].iloc[0]
    / ur5_start
)

print(
    f"\nFirst PartData UR3 time / "
    f"UR3 telemetry start = "
    f"{ur3_ratio_start:.6f}"
)

print(
    f"First PartData UR5 time / "
    f"UR5 telemetry start = "
    f"{ur5_ratio_start:.6f}"
)


# =============================================================================
# 13. KEY COVERAGE RESULT
# =============================================================================

print("\n" + "=" * 80)
print("COVERAGE RESULT")
print("=" * 80)

print(
    f"""
The dual-robot PLC telemetry provides approximately
{common_duration:.3f} seconds of common UR3/UR5 coverage.

The PartData production sequence spans approximately
{part['ur3_part_added_sec'].iloc[-1] - part['ur3_part_added_sec'].iloc[0]:.3f}
seconds between the first and last recorded part arrival.

Therefore the PLC robot telemetry is a partial capture relative to
the complete 60-part process record.

No specific PartData cycle range is assigned to the telemetry capture
by this script unless supported by an explicit clock relationship or
additional synchronization evidence.
"""
)


# =============================================================================
# 14. ANALYTICAL NOTE
# =============================================================================

print("=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
This script deliberately distinguishes:

1. Full-process coverage in PartData.
2. Partial high-frequency PLC telemetry coverage for UR3 and UR5.
3. Similar timing progression between process and robot clocks.
4. Proven synchronization from assumed absolute alignment.

High correlation of part-to-part intervals demonstrates common temporal
progression, but by itself does not identify which 273-second portion
of the full production run was captured by UR3Data.csv and UR5Data.csv.

A process-stage/robot-activity join should only be performed after the
telemetry capture's location within the production sequence is supported
by additional evidence.
"""
)