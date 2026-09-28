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
print("NIST DUAL-ROBOT TIMELINE ALIGNMENT AUDIT")
print("=" * 80)

print(f"\nPartData rows: {len(part):,}")
print(f"UR3 rows:      {len(ur3):,}")
print(f"UR5 rows:      {len(ur5):,}")


# =============================================================================
# 3. CONVERT DOCUMENTED ROBOT CLOCKS
# =============================================================================

# NIST documentation:
#
# UR3Data / UR5Data PLCTime -> divide by 10^7
# PartData UR3TimePartAdded / UR5TimePartAdded -> divide by 10^6

ur3["plc_time_sec"] = ur3["PLCTime"] / 1e7
ur5["plc_time_sec"] = ur5["PLCTime"] / 1e7

part["ur3_part_added_sec"] = (
    part["UR3TimePartAdded"] / 1e6
)

part["ur5_part_added_sec"] = (
    part["UR5TimePartAdded"] / 1e6
)


# =============================================================================
# 4. BASIC CLOCK RANGES
# =============================================================================

print("\n" + "=" * 80)
print("CLOCK RANGES")
print("=" * 80)

print("\nUR3 telemetry PLCTime:")
print(
    f"{ur3['plc_time_sec'].min():.6f} "
    f"to {ur3['plc_time_sec'].max():.6f} sec"
)

print("\nUR5 telemetry PLCTime:")
print(
    f"{ur5['plc_time_sec'].min():.6f} "
    f"to {ur5['plc_time_sec'].max():.6f} sec"
)

print("\nPartData UR3TimePartAdded:")
print(
    f"{part['ur3_part_added_sec'].min():.6f} "
    f"to {part['ur3_part_added_sec'].max():.6f} sec"
)

print("\nPartData UR5TimePartAdded:")
print(
    f"{part['ur5_part_added_sec'].min():.6f} "
    f"to {part['ur5_part_added_sec'].max():.6f} sec"
)


# =============================================================================
# 5. SAMPLING INTERVALS
# =============================================================================

print("\n" + "=" * 80)
print("ROBOT TELEMETRY SAMPLING")
print("=" * 80)

for name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    diff = robot["plc_time_sec"].diff().dropna()

    print(f"\n{name}")

    print(
        f"Median interval: "
        f"{diff.median():.6f} sec"
    )

    if diff.median() > 0:
        print(
            f"Approximate sampling rate: "
            f"{1 / diff.median():.2f} Hz"
        )

    print(
        f"Minimum interval: "
        f"{diff.min():.6f} sec"
    )

    print(
        f"Maximum interval: "
        f"{diff.max():.6f} sec"
    )

    print(
        f"Non-positive intervals: "
        f"{(diff <= 0).sum():,}"
    )


# =============================================================================
# 6. PARTDATA ROBOT CLOCK DIFFERENCE
# =============================================================================

print("\n" + "=" * 80)
print("UR3 vs UR5 PART-ADDED CLOCK DIFFERENCE")
print("=" * 80)

part["ur5_minus_ur3_part_added_sec"] = (
    part["ur5_part_added_sec"]
    - part["ur3_part_added_sec"]
)

print(
    part["ur5_minus_ur3_part_added_sec"]
    .describe()
    .round(6)
    .to_string()
)


# =============================================================================
# 7. PART-TO-PART ROBOT CLOCK INTERVALS
# =============================================================================

print("\n" + "=" * 80)
print("PART-TO-PART INTERVALS FROM ROBOT CLOCKS")
print("=" * 80)

part["ur3_part_interval_sec"] = (
    part["ur3_part_added_sec"].diff()
)

part["ur5_part_interval_sec"] = (
    part["ur5_part_added_sec"].diff()
)

print("\nUR3TimePartAdded intervals:")

print(
    part["ur3_part_interval_sec"]
    .dropna()
    .describe()
    .round(6)
    .to_string()
)

print("\nUR5TimePartAdded intervals:")

print(
    part["ur5_part_interval_sec"]
    .dropna()
    .describe()
    .round(6)
    .to_string()
)


# =============================================================================
# 8. COMPARE WITH PROCESS PartAdded INTERVALS
# =============================================================================

# PartData PLC event scale established in Script 04 as 10^7.

part["process_part_added_sec"] = (
    part["PartAdded"] / 1e7
)

part["process_part_interval_sec"] = (
    part["process_part_added_sec"].diff()
)

print("\n" + "=" * 80)
print("PROCESS vs ROBOT PART-TO-PART INTERVALS")
print("=" * 80)

comparison = pd.DataFrame({
    "process_interval_sec":
        part["process_part_interval_sec"],

    "ur3_interval_sec":
        part["ur3_part_interval_sec"],

    "ur5_interval_sec":
        part["ur5_part_interval_sec"],
}).dropna()

comparison["process_minus_ur3"] = (
    comparison["process_interval_sec"]
    - comparison["ur3_interval_sec"]
)

comparison["process_minus_ur5"] = (
    comparison["process_interval_sec"]
    - comparison["ur5_interval_sec"]
)

comparison["ur3_minus_ur5"] = (
    comparison["ur3_interval_sec"]
    - comparison["ur5_interval_sec"]
)

print("\nInterval comparison summary:")

print(
    comparison.describe()
    .T
    .round(6)
    .to_string()
)


# =============================================================================
# 9. INTERVAL CORRELATIONS
# =============================================================================

print("\n" + "=" * 80)
print("INTERVAL CORRELATIONS")
print("=" * 80)

print(
    comparison[
        [
            "process_interval_sec",
            "ur3_interval_sec",
            "ur5_interval_sec",
        ]
    ]
    .corr()
    .round(6)
    .to_string()
)


# =============================================================================
# 10. DIRECT TELEMETRY MATCH TEST
# =============================================================================

print("\n" + "=" * 80)
print("DIRECT CLOCK MATCH TEST")
print("=" * 80)

# Test whether PartData robot timestamps fall directly inside the
# UR3/UR5 PLCTime ranges.

ur3_inside = part["ur3_part_added_sec"].between(
    ur3["plc_time_sec"].min(),
    ur3["plc_time_sec"].max(),
)

ur5_inside = part["ur5_part_added_sec"].between(
    ur5["plc_time_sec"].min(),
    ur5["plc_time_sec"].max(),
)

print(
    f"\nUR3 PartData timestamps inside "
    f"UR3 telemetry range: "
    f"{ur3_inside.sum()} of {len(part)}"
)

print(
    f"UR5 PartData timestamps inside "
    f"UR5 telemetry range: "
    f"{ur5_inside.sum()} of {len(part)}"
)


# =============================================================================
# 11. OFFSET TEST
# =============================================================================

print("\n" + "=" * 80)
print("CLOCK OFFSET TEST")
print("=" * 80)

# Even if two clocks use different origins, their relative progression
# can still be aligned by subtracting the first observation.

process_relative = (
    part["process_part_added_sec"]
    - part["process_part_added_sec"].iloc[0]
)

ur3_relative = (
    part["ur3_part_added_sec"]
    - part["ur3_part_added_sec"].iloc[0]
)

ur5_relative = (
    part["ur5_part_added_sec"]
    - part["ur5_part_added_sec"].iloc[0]
)

relative = pd.DataFrame({
    "cycle_id": part["cycle_id"],
    "process_relative_sec": process_relative,
    "ur3_relative_sec": ur3_relative,
    "ur5_relative_sec": ur5_relative,
})

relative["process_minus_ur3_relative"] = (
    relative["process_relative_sec"]
    - relative["ur3_relative_sec"]
)

relative["process_minus_ur5_relative"] = (
    relative["process_relative_sec"]
    - relative["ur5_relative_sec"]
)

relative["ur3_minus_ur5_relative"] = (
    relative["ur3_relative_sec"]
    - relative["ur5_relative_sec"]
)

print("\nRelative-clock difference summary:")

print(
    relative[
        [
            "process_minus_ur3_relative",
            "process_minus_ur5_relative",
            "ur3_minus_ur5_relative",
        ]
    ]
    .describe()
    .T
    .round(6)
    .to_string()
)


# =============================================================================
# 12. FIRST AND LAST FIVE RELATIVE CLOCK OBSERVATIONS
# =============================================================================

print("\n" + "=" * 80)
print("RELATIVE CLOCK SAMPLE")
print("=" * 80)

print("\nFirst 5:")

print(
    relative.head(5)
    .round(6)
    .to_string(index=False)
)

print("\nLast 5:")

print(
    relative.tail(5)
    .round(6)
    .to_string(index=False)
)


# =============================================================================
# 13. NEAREST TELEMETRY TIMESTAMP TEST
# =============================================================================

print("\n" + "=" * 80)
print("NEAREST TELEMETRY TIMESTAMP TEST")
print("=" * 80)


def nearest_distance(reference_times, target_times):
    """
    Return absolute distance from each target timestamp
    to the nearest telemetry timestamp.
    """

    reference = np.sort(
        np.asarray(reference_times, dtype=float)
    )

    targets = np.asarray(
        target_times,
        dtype=float
    )

    positions = np.searchsorted(
        reference,
        targets
    )

    distances = []

    for target, position in zip(targets, positions):

        candidates = []

        if position < len(reference):
            candidates.append(
                abs(reference[position] - target)
            )

        if position > 0:
            candidates.append(
                abs(reference[position - 1] - target)
            )

        distances.append(
            min(candidates)
            if candidates
            else np.nan
        )

    return np.array(distances)


ur3_nearest_distance = nearest_distance(
    ur3["plc_time_sec"],
    part["ur3_part_added_sec"],
)

ur5_nearest_distance = nearest_distance(
    ur5["plc_time_sec"],
    part["ur5_part_added_sec"],
)

print("\nUR3 nearest telemetry timestamp distance:")

print(
    pd.Series(ur3_nearest_distance)
    .describe()
    .round(6)
    .to_string()
)

print("\nUR5 nearest telemetry timestamp distance:")

print(
    pd.Series(ur5_nearest_distance)
    .describe()
    .round(6)
    .to_string()
)


# =============================================================================
# 14. AUDIT INTERPRETATION
# =============================================================================

print("\n" + "=" * 80)
print("ALIGNMENT AUDIT NOTE")
print("=" * 80)

print(
    """
This script does not yet merge process events with robot telemetry.

Its purpose is to establish whether:

1. UR3 and UR5 PLC telemetry share a common time base.

2. UR3TimePartAdded and UR5TimePartAdded preserve the same
   part-to-part timing pattern as the process PartAdded events.

3. The clocks differ only by a fixed origin/offset, or whether
   scaling/drift must also be considered.

4. PartData robot timestamps can be directly matched to telemetry
   timestamps.

Only after these relationships are established should robot movement
be assigned to process-stage windows.
"""
)