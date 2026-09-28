from pathlib import Path

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

UR5_RTDE_FILE = (
    PROJECT_ROOT
    / "data"
    / "extracted"
    / "UR5RTDE.csv"
)


# =============================================================================
# 2. LOAD DATA
# =============================================================================

part = pd.read_csv(PARTDATA_FILE)
ur3 = pd.read_csv(UR3_FILE)
ur5 = pd.read_csv(UR5_FILE)

# UR5RTDE is whitespace-delimited.
ur5_rtde = pd.read_csv(
    UR5_RTDE_FILE,
    sep=r"\s+"
)


print("=" * 80)
print("NIST ROBOTIC WORK CELL - TIME SCALE RESOLUTION")
print("=" * 80)

print(f"\nPartData rows: {len(part):,}")
print(f"UR3 rows:      {len(ur3):,}")
print(f"UR5 rows:      {len(ur5):,}")
print(f"UR5RTDE rows:  {len(ur5_rtde):,}")


# =============================================================================
# 3. RAW PLC TIMESTAMP RANGES
# =============================================================================

print("\n" + "=" * 80)
print("RAW PLC TIMESTAMP RANGES")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    first = robot["PLCTime"].iloc[0]
    last = robot["PLCTime"].iloc[-1]
    difference = last - first

    print(f"\n{robot_name}")

    print(f"First raw PLCTime: {first:,.0f}")
    print(f"Last raw PLCTime:  {last:,.0f}")
    print(f"Raw difference:    {difference:,.0f}")


# =============================================================================
# 4. COMPETING PLC SCALE INTERPRETATIONS
# =============================================================================

print("\n" + "=" * 80)
print("COMPETING PLC TIME SCALES")
print("=" * 80)

scales = {
    "1e6": 1e6,
    "1e7": 1e7,
}

scale_results = []

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    raw_diff = (
        robot["PLCTime"]
        .diff()
        .dropna()
    )

    raw_duration = (
        robot["PLCTime"].iloc[-1]
        - robot["PLCTime"].iloc[0]
    )

    for scale_name, divisor in scales.items():

        duration_sec = (
            raw_duration / divisor
        )

        median_interval_sec = (
            raw_diff.median() / divisor
        )

        mean_interval_sec = (
            raw_diff.mean() / divisor
        )

        sampling_rate_hz = (
            1 / median_interval_sec
            if median_interval_sec > 0
            else float("nan")
        )

        scale_results.append({
            "robot": robot_name,
            "divisor": scale_name,
            "duration_sec": duration_sec,
            "duration_min": duration_sec / 60,
            "median_interval_sec":
                median_interval_sec,
            "mean_interval_sec":
                mean_interval_sec,
            "sampling_rate_hz":
                sampling_rate_hz,
        })


scale_df = pd.DataFrame(
    scale_results
)

print(
    scale_df
    .round(6)
    .to_string(index=False)
)


# =============================================================================
# 5. RAW PLC INCREMENT DISTRIBUTION
# =============================================================================

print("\n" + "=" * 80)
print("RAW PLC INCREMENT DISTRIBUTION")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    diff = (
        robot["PLCTime"]
        .diff()
        .dropna()
    )

    print(f"\n{robot_name}")

    print(
        diff.describe(
            percentiles=[
                0.01,
                0.05,
                0.25,
                0.50,
                0.75,
                0.95,
                0.99,
            ]
        )
        .round(3)
        .to_string()
    )

    print("\nMost common raw increments:")

    print(
        diff.value_counts()
        .head(10)
        .to_string()
    )


# =============================================================================
# 6. RTDE REFERENCE DURATION
# =============================================================================

print("\n" + "=" * 80)
print("UR5 RTDE REFERENCE")
print("=" * 80)

rtde_first = (
    ur5_rtde["timestamp"].iloc[0]
)

rtde_last = (
    ur5_rtde["timestamp"].iloc[-1]
)

rtde_duration = (
    rtde_last - rtde_first
)

rtde_diff = (
    ur5_rtde["timestamp"]
    .diff()
    .dropna()
)

print(
    f"\nFirst RTDE timestamp: "
    f"{rtde_first:.6f} sec"
)

print(
    f"Last RTDE timestamp:  "
    f"{rtde_last:.6f} sec"
)

print(
    f"RTDE duration:        "
    f"{rtde_duration:.6f} sec"
)

print(
    f"RTDE duration:        "
    f"{rtde_duration / 60:.4f} min"
)

print(
    f"Median interval:      "
    f"{rtde_diff.median():.6f} sec"
)

print(
    f"Approximate rate:     "
    f"{1 / rtde_diff.median():.2f} Hz"
)


# =============================================================================
# 7. PARTDATA ROBOT CLOCK DURATION
# =============================================================================

print("\n" + "=" * 80)
print("PARTDATA ROBOT CLOCK REFERENCE")
print("=" * 80)

part["ur3_part_added_sec"] = (
    part["UR3TimePartAdded"] / 1e6
)

part["ur5_part_added_sec"] = (
    part["UR5TimePartAdded"] / 1e6
)

ur3_part_duration = (
    part["ur3_part_added_sec"].iloc[-1]
    - part["ur3_part_added_sec"].iloc[0]
)

ur5_part_duration = (
    part["ur5_part_added_sec"].iloc[-1]
    - part["ur5_part_added_sec"].iloc[0]
)

print(
    f"\nUR3 PartAdded first-to-last: "
    f"{ur3_part_duration:.6f} sec "
    f"({ur3_part_duration / 60:.4f} min)"
)

print(
    f"UR5 PartAdded first-to-last: "
    f"{ur5_part_duration:.6f} sec "
    f"({ur5_part_duration / 60:.4f} min)"
)


# =============================================================================
# 8. TEST-PLAN REFERENCE
# =============================================================================

print("\n" + "=" * 80)
print("TEST-PLAN REFERENCE")
print("=" * 80)

# Setup and Testplan.txt reports:
# Start PLC Time: 3:27 PM
# PLC End time: around 4:15 PM
#
# The end time is explicitly approximate.

test_plan_minutes = 48
test_plan_seconds = test_plan_minutes * 60

print(
    f"\nApproximate documented interval: "
    f"{test_plan_minutes} min"
)

print(
    f"Approximate documented interval: "
    f"{test_plan_seconds} sec"
)

print(
    "\nNOTE: The test-plan end time is stated as "
    "'around 4:15PM', so this is not an exact benchmark."
)


# =============================================================================
# 9. DURATION COMPARISON
# =============================================================================

print("\n" + "=" * 80)
print("DURATION COMPARISON")
print("=" * 80)

duration_comparison = pd.DataFrame({
    "source": [
        "UR3 PLC using /1e6",
        "UR3 PLC using /1e7",
        "UR5 PLC using /1e6",
        "UR5 PLC using /1e7",
        "UR5 RTDE",
        "PartData UR3 first-last arrival",
        "PartData UR5 first-last arrival",
        "Test plan approximate window",
    ],

    "duration_sec": [
        (
            ur3["PLCTime"].iloc[-1]
            - ur3["PLCTime"].iloc[0]
        ) / 1e6,

        (
            ur3["PLCTime"].iloc[-1]
            - ur3["PLCTime"].iloc[0]
        ) / 1e7,

        (
            ur5["PLCTime"].iloc[-1]
            - ur5["PLCTime"].iloc[0]
        ) / 1e6,

        (
            ur5["PLCTime"].iloc[-1]
            - ur5["PLCTime"].iloc[0]
        ) / 1e7,

        rtde_duration,

        ur3_part_duration,

        ur5_part_duration,

        test_plan_seconds,
    ],
})

duration_comparison[
    "duration_min"
] = (
    duration_comparison["duration_sec"]
    / 60
)

duration_comparison[
    "difference_from_rtde_sec"
] = (
    duration_comparison["duration_sec"]
    - rtde_duration
)

print(
    duration_comparison
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 10. UR5 PLC vs UR5 RTDE DURATION MATCH
# =============================================================================

print("\n" + "=" * 80)
print("UR5 PLC vs UR5 RTDE DURATION MATCH")
print("=" * 80)

ur5_raw_duration = (
    ur5["PLCTime"].iloc[-1]
    - ur5["PLCTime"].iloc[0]
)

for scale_name, divisor in scales.items():

    plc_duration = (
        ur5_raw_duration / divisor
    )

    difference = (
        plc_duration - rtde_duration
    )

    relative_error_pct = (
        abs(difference)
        / rtde_duration
        * 100
    )

    print(
        f"\nDivisor {scale_name}"
    )

    print(
        f"PLC duration:       "
        f"{plc_duration:.6f} sec"
    )

    print(
        f"RTDE duration:      "
        f"{rtde_duration:.6f} sec"
    )

    print(
        f"Difference:         "
        f"{difference:.6f} sec"
    )

    print(
        f"Relative difference:"
        f" {relative_error_pct:.4f}%"
    )


# =============================================================================
# 11. EXPECTED SAMPLE COUNT UNDER EACH SCALE
# =============================================================================

print("\n" + "=" * 80)
print("SAMPLING INTERPRETATION")
print("=" * 80)

print(
    """
The same raw PLC increments produce very different physical
interpretations depending on the divisor:

    /1e7 -> approximately 0.0104 sec/sample
            approximately 96 samples/sec

    /1e6 -> approximately 0.104 sec/sample
            approximately 9.6 samples/sec

Duration consistency and sampling-rate plausibility must therefore
be considered together. Neither criterion should be used alone.
"""
)


# =============================================================================
# 12. SCALE CONSISTENCY SUMMARY
# =============================================================================

print("=" * 80)
print("SCALE CONSISTENCY SUMMARY")
print("=" * 80)

for robot_name, robot in [
    ("UR3", ur3),
    ("UR5", ur5),
]:

    raw_duration = (
        robot["PLCTime"].iloc[-1]
        - robot["PLCTime"].iloc[0]
    )

    duration_1e6 = (
        raw_duration / 1e6
    )

    duration_1e7 = (
        raw_duration / 1e7
    )

    print(f"\n{robot_name}")

    print(
        f"/1e6 duration: "
        f"{duration_1e6:.3f} sec "
        f"({duration_1e6 / 60:.3f} min)"
    )

    print(
        f"/1e7 duration: "
        f"{duration_1e7:.3f} sec "
        f"({duration_1e7 / 60:.3f} min)"
    )


# =============================================================================
# 13. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
The NIST README documents a 10^7 divisor for UR3Data and UR5Data
PLCTime values. That documented interpretation must not be silently
replaced.

However, the experiment-level duration implied by that divisor should
be checked against independent evidence:

- UR5 RTDE capture duration
- PartData production duration
- documented test-plan duration
- PLC sampling interval implied by each candidate divisor

If the documented divisor conflicts with multiple independent timing
references, the discrepancy should be reported explicitly and resolved
before process-stage telemetry alignment is attempted.
"""
)