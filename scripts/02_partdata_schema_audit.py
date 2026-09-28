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


# =============================================================================
# 2. RAW CSV STRUCTURE AUDIT
# =============================================================================

print("=" * 80)
print("PARTDATA SCHEMA AUDIT")
print("=" * 80)

with INPUT_FILE.open("r", newline="", encoding="utf-8-sig") as f:
    rows = list(csv.reader(f))

header = rows[0]
data_rows = rows[1:]

print(f"\nHeader fields:       {len(header)}")
print(f"Data rows:           {len(data_rows):,}")

row_lengths = pd.Series(
    [len(row) for row in data_rows],
    name="field_count"
)

print("\nRaw data-row field counts:")
print(row_lengths.value_counts().sort_index().to_string())


# =============================================================================
# 3. DISPLAY HEADER POSITIONS
# =============================================================================

print("\n" + "=" * 80)
print("HEADER POSITIONS")
print("=" * 80)

for i, column in enumerate(header, start=1):
    print(f"{i:>2}: {column}")


# =============================================================================
# 4. COMPARE RAW VALUES WITH HEADER POSITIONS
# =============================================================================

print("\n" + "=" * 80)
print("FIRST RAW RECORD - POSITIONAL COMPARISON")
print("=" * 80)

first_row = data_rows[0]

max_fields = max(len(header), len(first_row))

for i in range(max_fields):

    header_value = header[i] if i < len(header) else "<NO HEADER>"
    row_value = first_row[i] if i < len(first_row) else "<NO VALUE>"

    print(
        f"{i + 1:>2}: "
        f"{header_value:<28} -> {row_value}"
    )


# =============================================================================
# 5. PANDAS INTERPRETATION
# =============================================================================

df = pd.read_csv(INPUT_FILE)

print("\n" + "=" * 80)
print("PANDAS INTERPRETATION")
print("=" * 80)

print(f"\nShape: {df.shape}")

print("\nFirst 3 rows:")
print(df.head(3).to_string(index=True))


# =============================================================================
# 6. MISSINGNESS
# =============================================================================

print("\n" + "=" * 80)
print("MISSINGNESS")
print("=" * 80)

missing = pd.DataFrame({
    "missing_count": df.isna().sum(),
    "missing_pct": df.isna().mean() * 100
})

missing = missing[missing["missing_count"] > 0]

if missing.empty:
    print("\nNo missing values.")
else:
    print()
    print(missing.to_string())


# =============================================================================
# 7. CARDINALITY / UNIQUE VALUES
# =============================================================================

print("\n" + "=" * 80)
print("LOW-CARDINALITY FIELDS")
print("=" * 80)

for column in df.columns:

    unique_count = df[column].nunique(dropna=False)

    if unique_count <= 10:
        print(f"\n{column}")
        print(df[column].value_counts(dropna=False).to_string())


# =============================================================================
# 8. NIST PROCESS EVENT FIELDS
# =============================================================================

# Mapping taken from the NIST UseCaseTimeline.
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
    "PutputPartPlaced",        # t12 - spelling preserved from source
    "PlaceInOutputComplete",   # t13
    "PartRemoved",             # t14
]


print("\n" + "=" * 80)
print("NIST t1-t14 EVENT COMPLETENESS")
print("=" * 80)

for i, column in enumerate(event_columns, start=1):

    populated = df[column].notna().sum()
    missing_count = df[column].isna().sum()

    print(
        f"t{i:<2} "
        f"{column:<26} "
        f"populated={populated:>2} "
        f"missing={missing_count:>2}"
    )


# =============================================================================
# 9. EVENT ORDER CHECK
# =============================================================================

print("\n" + "=" * 80)
print("EVENT ORDER CHECK")
print("=" * 80)

# Only use event columns that are actually populated.
available_events = [
    column
    for column in event_columns
    if df[column].notna().any()
]

event_values = df[available_events]

differences = event_values.diff(axis=1)

non_positive = (differences.iloc[:, 1:] <= 0).sum()

print("\nNon-positive transitions by event:")

for column, count in non_positive.items():
    print(f"{column:<28} {count:>3}")


rows_with_order_problem = (
    differences.iloc[:, 1:] <= 0
).any(axis=1)

print(
    f"\nRows with at least one non-positive "
    f"event transition: {rows_with_order_problem.sum():,}"
)


# =============================================================================
# 10. RAW FINAL-FIELD CHECK
# =============================================================================

print("\n" + "=" * 80)
print("RAW FINAL FIELD CHECK")
print("=" * 80)

final_values = [
    row[-1] if len(row) > 0 else ""
    for row in data_rows
]

blank_final_values = sum(value.strip() == "" for value in final_values)

print(f"\nRows:                    {len(data_rows):,}")
print(f"Blank final raw values:  {blank_final_values:,}")


# =============================================================================
# 11. AUDIT NOTES
# =============================================================================

print("\n" + "=" * 80)
print("AUDIT INTERPRETATION")
print("=" * 80)

print(
    """
This script does not modify PartData.csv.

Its purpose is to determine:

1. Whether the supplied CSV header contains the same number of fields
   as each raw data record.

2. How pandas is interpreting any header/data-width mismatch.

3. Whether the apparent PartRemoved field (t14) is populated.

4. Whether the populated NIST process timestamps preserve the expected
   t1 -> t14 chronological order.

No cycle-time calculations or schema corrections should be performed
until this audit has been reviewed.
"""
)