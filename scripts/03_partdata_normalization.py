from pathlib import Path
import csv

import pandas as pd


# =============================================================================
# 1. PATHS
# =============================================================================

PROJECT_ROOT = Path(
    r"C:\Users\Hp\Industrial-Analytics"
    r"\NIST Robotic Work Cell Operational Analytics"
)

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "extracted"
    / "PLC Data"
    / "PartData.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "partdata_normalized.csv"


# =============================================================================
# 2. READ RAW CSV
# =============================================================================

with INPUT_FILE.open("r", newline="", encoding="utf-8-sig") as f:
    rows = list(csv.reader(f))

header = rows[0]
raw_rows = rows[1:]

print("=" * 80)
print("PARTDATA NORMALIZATION")
print("=" * 80)

print(f"\nHeader fields: {len(header)}")
print(f"Raw data rows: {len(raw_rows):,}")


# =============================================================================
# 3. VALIDATE RAW ROW STRUCTURE
# =============================================================================

expected_fields = len(header)

unexpected_rows = []

for row_number, row in enumerate(raw_rows, start=2):

    # The NIST source contains one confirmed empty trailing field
    # after the 22 meaningful values.
    valid_structure = (
        len(row) == expected_fields + 1
        and row[-1].strip() == ""
    )

    if not valid_structure:
        unexpected_rows.append(
            (row_number, len(row), row[-1] if row else None)
        )

print(
    f"Rows with expected 22 values + "
    f"1 empty trailing field: "
    f"{len(raw_rows) - len(unexpected_rows):,}"
)

print(f"Unexpected raw rows: {len(unexpected_rows):,}")

if unexpected_rows:
    print("\nUnexpected row structures:")
    for item in unexpected_rows[:10]:
        print(item)

    raise ValueError(
        "Unexpected PartData row structure detected. "
        "Normalization stopped."
    )


# =============================================================================
# 4. REMOVE ONLY THE CONFIRMED EMPTY TRAILING FIELD
# =============================================================================

clean_rows = [
    row[:expected_fields]
    for row in raw_rows
]

df = pd.DataFrame(clean_rows, columns=header)

print("\nNormalized shape:", df.shape)


# =============================================================================
# 5. APPLY DATA TYPES
# =============================================================================

integer_columns = [
    "Part Number",
    "Work Fixture",
    "Input Position",
    "Output Position",
    "Part Type",
    "UR3TimePartAdded",
    "UR5TimePartAdded",
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

for column in integer_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="raise"
    ).astype("int64")

complete_map = {
    "TRUE": True,
    "FALSE": False,
}

unexpected_complete = set(df["Complete"]) - set(complete_map)

if unexpected_complete:
    raise ValueError(
        f"Unexpected Complete values: {unexpected_complete}"
    )

df["Complete"] = df["Complete"].map(complete_map)


# =============================================================================
# 6. BASIC VALIDATION
# =============================================================================

print("\n" + "=" * 80)
print("NORMALIZED DATA VALIDATION")
print("=" * 80)

print(f"\nRows:              {len(df):,}")
print(f"Columns:           {df.shape[1]:,}")
print(f"Missing cells:     {df.isna().sum().sum():,}")
print(f"Duplicate rows:    {df.duplicated().sum():,}")

print("\nFirst 3 rows:")
print(df.head(3).to_string(index=False))


# =============================================================================
# 7. NIST t1-t14 EVENT MAPPING
# =============================================================================

event_columns = [
    "PartAdded",               # t1
    "PickFromInputAssigned",   # t2
    "InputPartPicked",         # t3
    "InputPartPlaced",         # t4
    "PlaceInWFComplete",       # t5
    "TaskAssigned",            # t6
    "TaskActionStart",         # t7
    "TaskActionComplete",      # t8
    "TaskComplete",            # t9
    "PickFromWFAssigned",      # t10
    "OutputPartPicked",        # t11
    "PutputPartPlaced",        # t12
    "PlaceInOutputComplete",   # t13
    "PartRemoved",             # t14
]


# =============================================================================
# 8. EVENT COMPLETENESS
# =============================================================================

print("\n" + "=" * 80)
print("t1-t14 EVENT COMPLETENESS")
print("=" * 80)

for i, column in enumerate(event_columns, start=1):

    populated = df[column].notna().sum()
    missing = df[column].isna().sum()

    print(
        f"t{i:<2} "
        f"{column:<26} "
        f"populated={populated:>2} "
        f"missing={missing:>2}"
    )


# =============================================================================
# 9. CHRONOLOGICAL EVENT ORDER
# =============================================================================

print("\n" + "=" * 80)
print("t1-t14 CHRONOLOGICAL ORDER")
print("=" * 80)

event_diff = df[event_columns].diff(axis=1)

transition_issues = (
    event_diff.iloc[:, 1:] <= 0
).sum()

for column, count in transition_issues.items():
    print(f"{column:<28} {count:>3}")

rows_with_order_issue = (
    event_diff.iloc[:, 1:] <= 0
).any(axis=1)

print(
    f"\nRows with at least one "
    f"non-positive transition: "
    f"{rows_with_order_issue.sum():,}"
)


# =============================================================================
# 10. ROBOT-TIME FIELDS
# =============================================================================

print("\n" + "=" * 80)
print("ROBOT TIME FIELDS")
print("=" * 80)

for column in [
    "UR3TimePartAdded",
    "UR5TimePartAdded",
]:

    seconds = df[column] / 1e6

    print(f"\n{column}")
    print(f"Raw minimum:       {df[column].min():,}")
    print(f"Raw maximum:       {df[column].max():,}")
    print(f"Minimum / 1e6:     {seconds.min():.6f} s")
    print(f"Maximum / 1e6:     {seconds.max():.6f} s")


# =============================================================================
# 11. PLC EVENT TIMESTAMP DIFFERENCES
# =============================================================================

print("\n" + "=" * 80)
print("PLC EVENT TIMESTAMP DIFFERENCES")
print("=" * 80)

# We deliberately inspect raw differences first.
# The NIST README supplied with the dataset has an incomplete
# exponent for conversion of these PLC event timestamps.
#
# Therefore this script does NOT yet assume a seconds conversion.

transition_names = []

transition_raw_diffs = pd.DataFrame(index=df.index)

for i in range(len(event_columns) - 1):

    start = event_columns[i]
    end = event_columns[i + 1]

    name = f"t{i + 1}_to_t{i + 2}"

    transition_names.append(name)

    transition_raw_diffs[name] = (
        df[end] - df[start]
    )


summary = transition_raw_diffs.describe().T[
    ["min", "50%", "mean", "max"]
]

print("\nRaw timestamp differences:")
print(summary.to_string())


# =============================================================================
# 12. OVERALL t1-to-t14 RAW DURATION
# =============================================================================

overall_raw = (
    df["PartRemoved"]
    - df["PartAdded"]
)

print("\n" + "=" * 80)
print("OVERALL t1-to-t14 RAW DURATION")
print("=" * 80)

print(
    overall_raw.describe()[
        ["min", "50%", "mean", "max"]
    ].to_string()
)


# =============================================================================
# 13. ADD ANALYTICAL IDENTIFIER
# =============================================================================

# Part Number is not unique across the 60 observations.
# Preserve it exactly as supplied and add a separate analytical row identifier.

df.insert(
    0,
    "cycle_id",
    range(1, len(df) + 1)
)


# =============================================================================
# 14. SAVE NORMALIZED DATA
# =============================================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n" + "=" * 80)
print("OUTPUT")
print("=" * 80)

print(f"\nSaved normalized dataset to:")
print(OUTPUT_FILE)

print(f"\nFinal shape: {df.shape}")


# =============================================================================
# 15. INTERPRETATION NOTES
# =============================================================================

print("\n" + "=" * 80)
print("NORMALIZATION NOTES")
print("=" * 80)

print(
    """
1. The original NIST PartData.csv was not modified.

2. Each raw record contains the 22 values defined by the header,
   followed by one empty trailing CSV field.

3. The trailing empty field was removed during normalization.

4. The source spelling 'PutputPartPlaced' is deliberately preserved
   at this stage to maintain traceability to the raw source.

5. cycle_id is an analytical identifier only. The original
   Part Number field is preserved.

6. NIST documents UR3TimePartAdded and UR5TimePartAdded as robot
   times requiring division by 10^6 to convert to seconds.

7. No conversion has yet been imposed on the 14 PLC event timestamps
   because the supplied README contains an incomplete exponent.

8. Process-stage durations should not be finalized until the PLC
   timestamp scale has been established from the evidence.
"""
)