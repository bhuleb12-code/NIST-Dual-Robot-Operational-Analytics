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

PLC_DIR = PROJECT_ROOT / "data" / "extracted" / "PLC Data"
EXTRACTED_DIR = PROJECT_ROOT / "data" / "extracted"

FILES = {
    "PartData": PLC_DIR / "PartData.csv",
    "UR3Data": PLC_DIR / "UR3Data.csv",
    "UR5Data": PLC_DIR / "UR5Data.csv",
    "UR5RTDE": EXTRACTED_DIR / "UR5RTDE.csv",
}


# =============================================================================
# 2. LOAD DATA
# =============================================================================

part = pd.read_csv(FILES["PartData"])
ur3 = pd.read_csv(FILES["UR3Data"])
ur5 = pd.read_csv(FILES["UR5Data"])

# RTDE file is whitespace-delimited.
ur5_rtde = pd.read_csv(
    FILES["UR5RTDE"],
    sep=r"\s+"
)

datasets = {
    "PartData": part,
    "UR3Data": ur3,
    "UR5Data": ur5,
    "UR5RTDE": ur5_rtde,
}


# =============================================================================
# 3. BASIC INVENTORY
# =============================================================================

print("=" * 80)
print("NIST ROBOTIC WORK CELL - DATA INVENTORY")
print("=" * 80)

for name, df in datasets.items():

    print(f"\n{name}")
    print("-" * 80)

    print(f"Rows:              {len(df):,}")
    print(f"Columns:           {df.shape[1]:,}")
    print(f"Missing cells:     {df.isna().sum().sum():,}")
    print(f"Duplicate rows:    {df.duplicated().sum():,}")

    numeric = df.select_dtypes(include=np.number)

    if not numeric.empty:
        infinite_count = np.isinf(numeric).sum().sum()
        print(f"Infinite values:   {infinite_count:,}")


# =============================================================================
# 4. PLC ROBOT TIME COVERAGE
# =============================================================================

print("\n" + "=" * 80)
print("PLC ROBOT TIME COVERAGE")
print("=" * 80)

for name, df in {
    "UR3Data": ur3,
    "UR5Data": ur5,
}.items():

    plc_seconds = df["PLCTime"] / 1e7

    print(f"\n{name}")
    print(f"First PLC time:    {plc_seconds.iloc[0]:.4f} s")
    print(f"Last PLC time:     {plc_seconds.iloc[-1]:.4f} s")
    print(
        f"Duration:          "
        f"{plc_seconds.iloc[-1] - plc_seconds.iloc[0]:.4f} s"
    )


# =============================================================================
# 5. UR5 RTDE TIME COVERAGE
# =============================================================================

print("\n" + "=" * 80)
print("UR5 RTDE TIME COVERAGE")
print("=" * 80)

rtde_time = ur5_rtde["timestamp"]

rtde_duration = rtde_time.iloc[-1] - rtde_time.iloc[0]
rtde_interval = rtde_time.diff().dropna()

print(f"First timestamp:       {rtde_time.iloc[0]:.6f} s")
print(f"Last timestamp:        {rtde_time.iloc[-1]:.6f} s")
print(f"Duration:              {rtde_duration:.6f} s")
print(f"Median interval:       {rtde_interval.median():.6f} s")
print(
    f"Approx sample rate:    "
    f"{1 / rtde_interval.median():.2f} Hz"
)


# =============================================================================
# 6. SCHEMA
# =============================================================================

print("\n" + "=" * 80)
print("DATASET SCHEMAS")
print("=" * 80)

for name, df in datasets.items():

    print(f"\n{name}")
    print("-" * 80)

    for column in df.columns:
        print(f"{column:<35} {str(df[column].dtype):<15}")


# =============================================================================
# 7. IMPORTANT SOURCE NOTES
# =============================================================================

print("\n" + "=" * 80)
print("SOURCE / INTERPRETATION NOTES")
print("=" * 80)

print(
    """
1. UR3Data and UR5Data PLCTime values are divided by 10^7
   to convert to seconds, according to the NIST README.

2. RobotTime conversion documented by NIST is 10^6.

3. UR5RTDE is whitespace-delimited and contains high-frequency
   UR5 telemetry.

4. PartData contains 14 process-event timestamps corresponding
   to the NIST UseCaseTimeline.

5. The raw PartData header/row structure requires further audit
   before process durations are calculated.

6. Raw source files must remain unchanged. Any corrections or
   normalized fields will be written to processed data.
"""
)