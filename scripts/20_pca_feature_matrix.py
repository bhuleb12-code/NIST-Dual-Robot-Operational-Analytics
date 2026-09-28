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

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PARTDATA_FILE = (
    PROCESSED_DIR
    / "partdata_normalized.csv"
)

UR3_FILE = (
    PROCESSED_DIR
    / "ur3_operational_features.csv"
)

UR5_FILE = (
    PROCESSED_DIR
    / "ur5_operational_features.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "pca_process_stage_features.csv"
)


# =============================================================================
# 2. CONSTANTS
# =============================================================================

# Robot PLC telemetry:
#
# Script 08 established that UR3Data / UR5Data PLCTime must use /1e6
# for analytical synchronization across the experiment.
PLC_ANALYTICAL_DIVISOR = 1e6


# PartData process-event timestamps:
#
# Event differences use /1e7 to produce physically plausible process-stage
# durations.
#
# IMPORTANT:
# These converted event values are NOT treated as absolute robot telemetry
# timestamps.
#
# Instead, event times are expressed as offsets relative to PartAdded and
# then added to each robot's cycle-specific PartAdded anchor.
PART_EVENT_DIVISOR = 1e7


# =============================================================================
# 3. PROCESS EVENTS
# =============================================================================

EVENTS = [
    ("t1", "PartAdded"),
    ("t2", "PickFromInputAssigned"),
    ("t3", "InputPartPicked"),
    ("t4", "InputPartPlaced"),
    ("t5", "PlaceInWFComplete"),
    ("t6", "TaskAssigned"),
    ("t7", "TaskActionStart"),
    ("t8", "TaskActionComplete"),
    ("t9", "TaskComplete"),
    ("t10", "PickFromWFAssigned"),
    ("t11", "OutputPartPicked"),
    ("t12", "PutputPartPlaced"),
    ("t13", "PlaceInOutputComplete"),
    ("t14", "PartRemoved"),
]


STAGES = [
    (
        "t1_t2",
        "PartAdded",
        "PickFromInputAssigned",
    ),
    (
        "t2_t3",
        "PickFromInputAssigned",
        "InputPartPicked",
    ),
    (
        "t3_t4",
        "InputPartPicked",
        "InputPartPlaced",
    ),
    (
        "t4_t5",
        "InputPartPlaced",
        "PlaceInWFComplete",
    ),
    (
        "t5_t6",
        "PlaceInWFComplete",
        "TaskAssigned",
    ),
    (
        "t6_t7",
        "TaskAssigned",
        "TaskActionStart",
    ),
    (
        "t7_t8",
        "TaskActionStart",
        "TaskActionComplete",
    ),
    (
        "t8_t9",
        "TaskActionComplete",
        "TaskComplete",
    ),
    (
        "t9_t10",
        "TaskComplete",
        "PickFromWFAssigned",
    ),
    (
        "t10_t11",
        "PickFromWFAssigned",
        "OutputPartPicked",
    ),
    (
        "t11_t12",
        "OutputPartPicked",
        "PutputPartPlaced",
    ),
    (
        "t12_t13",
        "PutputPartPlaced",
        "PlaceInOutputComplete",
    ),
    (
        "t13_t14",
        "PlaceInOutputComplete",
        "PartRemoved",
    ),
]


POSITION_COLUMNS = [
    f"j{i}_qactual"
    for i in range(1, 7)
]

VELOCITY_COLUMNS = [
    f"j{i}_qdactual"
    for i in range(1, 7)
]


# =============================================================================
# 4. LOAD DATA
# =============================================================================

print("=" * 90)
print("NIST ROBOTIC WORK CELL - PCA PROCESS-STAGE FEATURE MATRIX")
print("=" * 90)


def load_required_csv(path, label):

    if not path.exists():
        raise FileNotFoundError(
            f"{label} not found:\n{path}"
        )

    df = pd.read_csv(path)

    print(
        f"{label:<30} "
        f"shape={df.shape}"
    )

    return df


partdata = load_required_csv(
    PARTDATA_FILE,
    "PartData normalized",
)

ur3 = load_required_csv(
    UR3_FILE,
    "UR3 operational features",
)

ur5 = load_required_csv(
    UR5_FILE,
    "UR5 operational features",
)


# =============================================================================
# 5. VALIDATE REQUIRED COLUMNS
# =============================================================================

def require_columns(
    df,
    columns,
    label,
):

    missing = [
        col
        for col in columns
        if col not in df.columns
    ]

    if missing:

        raise ValueError(
            f"{label} missing required columns: "
            f"{missing}"
        )


part_required = [
    "cycle_id",
    "Work Fixture",
    "UR3TimePartAdded",
    "UR5TimePartAdded",
]


for _, event_column in EVENTS:

    part_required.append(
        event_column
    )


part_required = list(
    dict.fromkeys(
        part_required
    )
)


require_columns(
    partdata,
    part_required,
    "PartData",
)


telemetry_required = (
    ["PLCTime"]
    + POSITION_COLUMNS
    + VELOCITY_COLUMNS
)


require_columns(
    ur3,
    telemetry_required,
    "UR3 telemetry",
)

require_columns(
    ur5,
    telemetry_required,
    "UR5 telemetry",
)


# =============================================================================
# 6. PREPARE PARTDATA CLOCK BRIDGE
# =============================================================================

# Convert required timing columns to numeric.

timing_columns = [
    "UR3TimePartAdded",
    "UR5TimePartAdded",
]

timing_columns.extend(
    [
        event_column
        for _, event_column in EVENTS
    ]
)


for col in timing_columns:

    partdata[col] = pd.to_numeric(
        partdata[col],
        errors="coerce",
    )


# -----------------------------------------------------------------------------
# Cycle-specific robot PartAdded anchors.
#
# These are the bridge between the PartData process record and each robot's
# telemetry clock.
# -----------------------------------------------------------------------------

partdata[
    "ur3_anchor_sec"
] = (
    partdata[
        "UR3TimePartAdded"
    ]
    / PLC_ANALYTICAL_DIVISOR
)

partdata[
    "ur5_anchor_sec"
] = (
    partdata[
        "UR5TimePartAdded"
    ]
    / PLC_ANALYTICAL_DIVISOR
)


# -----------------------------------------------------------------------------
# Process-event offsets relative to PartAdded.
#
# The PartData process-event clock is not directly equated with the robot
# telemetry clock.
#
# Instead:
#
# robot event time
#     =
# robot PartAdded anchor
#     +
# (event timestamp - PartAdded timestamp) / 1e7
# -----------------------------------------------------------------------------

for event_label, event_column in EVENTS:

    relative_offset = (
        partdata[
            event_column
        ]
        - partdata[
            "PartAdded"
        ]
    ) / PART_EVENT_DIVISOR

    partdata[
        f"{event_label}_offset_sec"
    ] = relative_offset

    partdata[
        f"ur3_{event_label}_sec"
    ] = (
        partdata[
            "ur3_anchor_sec"
        ]
        + relative_offset
    )

    partdata[
        f"ur5_{event_label}_sec"
    ] = (
        partdata[
            "ur5_anchor_sec"
        ]
        + relative_offset
    )


# =============================================================================
# 7. PREPARE ROBOT TELEMETRY
# =============================================================================

def prepare_telemetry(
    df,
    label,
):

    output = df.copy()

    # -------------------------------------------------------------------------
    # Reconstruct the validated robot PLC clock directly from raw PLCTime.
    #
    # Earlier operational-feature files contain plc_time_sec created before
    # the timing-scale discrepancy was resolved. Therefore we do not trust
    # that stored derived column here.
    # -------------------------------------------------------------------------

    output[
        "PLCTime"
    ] = pd.to_numeric(
        output[
            "PLCTime"
        ],
        errors="coerce",
    )

    output[
        "plc_time_sec"
    ] = (
        output[
            "PLCTime"
        ]
        / PLC_ANALYTICAL_DIVISOR
    )


    numeric_columns = (
        ["plc_time_sec"]
        + POSITION_COLUMNS
        + VELOCITY_COLUMNS
    )


    for col in numeric_columns:

        output[col] = pd.to_numeric(
            output[col],
            errors="coerce",
        )


    output = output.replace(
        [np.inf, -np.inf],
        np.nan,
    )


    output = (
        output
        .sort_values(
            "plc_time_sec"
        )
        .reset_index(
            drop=True
        )
    )


    print(
        f"\n{label} telemetry range:"
    )

    print(
        f"  Start: "
        f"{output['plc_time_sec'].min():.3f} sec"
    )

    print(
        f"  End:   "
        f"{output['plc_time_sec'].max():.3f} sec"
    )


    return output


ur3 = prepare_telemetry(
    ur3,
    "UR3",
)

ur5 = prepare_telemetry(
    ur5,
    "UR5",
)


# =============================================================================
# 8. CLOCK-BRIDGE SANITY CHECK
# =============================================================================

print("\n" + "=" * 90)
print("CLOCK-BRIDGE SANITY CHECK")
print("=" * 90)


print(
    "\nFirst five cycle anchors:"
)

print(
    partdata[
        [
            "cycle_id",
            "ur3_anchor_sec",
            "ur5_anchor_sec",
            "t14_offset_sec",
        ]
    ]
    .head()
    .round(4)
    .to_string(
        index=False
    )
)


total_process_duration = (
    partdata[
        "t14_offset_sec"
    ]
    - partdata[
        "t1_offset_sec"
    ]
)


print(
    "\nPartAdded -> PartRemoved duration:"
)

print(
    total_process_duration
    .describe()
    .round(4)
    .to_string()
)


# =============================================================================
# 9. TELEMETRY FEATURE FUNCTION
# =============================================================================

def telemetry_features(
    telemetry,
    start_sec,
    end_sec,
    robot_prefix,
):

    """
    Calculate process-stage motion features for one robot.

    Each stage window is expressed in that robot's own PLC telemetry
    clock using the cycle-specific clock bridge.
    """

    result = {
        f"{robot_prefix}_observations":
            0,

        f"{robot_prefix}_speed_abs_mean":
            np.nan,

        f"{robot_prefix}_speed_abs_std":
            np.nan,

        f"{robot_prefix}_speed_abs_max":
            np.nan,

        f"{robot_prefix}_joint_path":
            np.nan,

        f"{robot_prefix}_joint_net_change":
            np.nan,

        f"{robot_prefix}_position_variability":
            np.nan,
    }


    if (
        pd.isna(start_sec)
        or pd.isna(end_sec)
        or end_sec <= start_sec
    ):

        return result


    # Use a half-open interval [start, end), matching the established
    # synchronization logic from Script 09.

    mask = (
        (
            telemetry[
                "plc_time_sec"
            ] >= start_sec
        )
        &
        (
            telemetry[
                "plc_time_sec"
            ] < end_sec
        )
    )


    window = telemetry.loc[
        mask
    ].copy()


    result[
        f"{robot_prefix}_observations"
    ] = len(window)


    if len(window) == 0:

        return result


    # -------------------------------------------------------------------------
    # Joint velocity magnitude
    # -------------------------------------------------------------------------

    velocity = (
        window[
            VELOCITY_COLUMNS
        ]
        .abs()
    )


    sample_mean_speed = (
        velocity.mean(
            axis=1
        )
    )


    result[
        f"{robot_prefix}_speed_abs_mean"
    ] = (
        sample_mean_speed.mean()
    )


    # ddof=0 is used so that a one-sample stage window receives zero
    # within-window variability rather than NaN.
    #
    # This is especially relevant for very short process stages.

    result[
        f"{robot_prefix}_speed_abs_std"
    ] = (
        sample_mean_speed.std(
            ddof=0
        )
    )


    result[
        f"{robot_prefix}_speed_abs_max"
    ] = (
        velocity
        .max(
            axis=1
        )
        .max()
    )


    # -------------------------------------------------------------------------
    # Joint-position movement
    # -------------------------------------------------------------------------

    positions = window[
        POSITION_COLUMNS
    ]


    if len(positions) >= 2:

        joint_path = (
            positions
            .diff()
            .abs()
            .sum(
                axis=1
            )
            .sum()
        )


        joint_net_change = (
            (
                positions.iloc[-1]
                - positions.iloc[0]
            )
            .abs()
            .sum()
        )

    else:

        joint_path = 0.0
        joint_net_change = 0.0


    result[
        f"{robot_prefix}_joint_path"
    ] = joint_path


    result[
        f"{robot_prefix}_joint_net_change"
    ] = joint_net_change


    # -------------------------------------------------------------------------
    # Joint-position variability
    # -------------------------------------------------------------------------

    result[
        f"{robot_prefix}_position_variability"
    ] = (
        positions
        .std(
            ddof=0
        )
        .mean()
    )


    return result


# =============================================================================
# 10. BUILD PROCESS-STAGE OBSERVATIONS
# =============================================================================

print("\n" + "=" * 90)
print("BUILDING PROCESS-STAGE OBSERVATIONS")
print("=" * 90)


event_to_label = {
    event_column: event_label
    for event_label, event_column in EVENTS
}


rows = []


for _, part in partdata.iterrows():

    cycle_id = int(
        part[
            "cycle_id"
        ]
    )

    fixture = part[
        "Work Fixture"
    ]


    for (
        stage_name,
        start_event,
        end_event,
    ) in STAGES:

        start_label = (
            event_to_label[
                start_event
            ]
        )

        end_label = (
            event_to_label[
                end_event
            ]
        )


        start_offset_sec = (
            part[
                f"{start_label}_offset_sec"
            ]
        )

        end_offset_sec = (
            part[
                f"{end_label}_offset_sec"
            ]
        )


        if (
            pd.isna(start_offset_sec)
            or pd.isna(end_offset_sec)
        ):

            continue


        stage_duration_sec = (
            end_offset_sec
            - start_offset_sec
        )


        # ---------------------------------------------------------------------
        # Separate synchronized windows for UR3 and UR5.
        # ---------------------------------------------------------------------

        ur3_start_sec = (
            part[
                f"ur3_{start_label}_sec"
            ]
        )

        ur3_end_sec = (
            part[
                f"ur3_{end_label}_sec"
            ]
        )

        ur5_start_sec = (
            part[
                f"ur5_{start_label}_sec"
            ]
        )

        ur5_end_sec = (
            part[
                f"ur5_{end_label}_sec"
            ]
        )


        ur3_metrics = telemetry_features(
            ur3,
            ur3_start_sec,
            ur3_end_sec,
            "ur3",
        )


        ur5_metrics = telemetry_features(
            ur5,
            ur5_start_sec,
            ur5_end_sec,
            "ur5",
        )


        row = {
            "cycle_id":
                cycle_id,

            "work_fixture":
                fixture,

            "stage":
                stage_name,

            "stage_start_event":
                start_event,

            "stage_end_event":
                end_event,

            "stage_start_offset_sec":
                start_offset_sec,

            "stage_end_offset_sec":
                end_offset_sec,

            "stage_duration_sec":
                stage_duration_sec,

            "ur3_stage_start_sec":
                ur3_start_sec,

            "ur3_stage_end_sec":
                ur3_end_sec,

            "ur5_stage_start_sec":
                ur5_start_sec,

            "ur5_stage_end_sec":
                ur5_end_sec,
        }


        row.update(
            ur3_metrics
        )

        row.update(
            ur5_metrics
        )


        rows.append(
            row
        )


stage_features = pd.DataFrame(
    rows
)


print(
    f"\nProcess-stage observations created: "
    f"{len(stage_features)}"
)

print(
    f"Cycles represented: "
    f"{stage_features['cycle_id'].nunique()}"
)

print(
    f"Stages represented: "
    f"{stage_features['stage'].nunique()}"
)


# =============================================================================
# 11. DERIVED MOTION-RATE FEATURES
# =============================================================================

# Accumulated path depends partly on stage duration.
#
# Path-per-second provides a duration-normalized movement measure.

for robot in [
    "ur3",
    "ur5",
]:

    stage_features[
        f"{robot}_joint_path_per_sec"
    ] = np.where(
        stage_features[
            "stage_duration_sec"
        ] > 0,

        stage_features[
            f"{robot}_joint_path"
        ]
        /
        stage_features[
            "stage_duration_sec"
        ],

        np.nan,
    )


# =============================================================================
# 12. DUAL-ROBOT RELATIVE FEATURES
# =============================================================================

stage_features[
    "combined_speed_abs_mean"
] = (
    stage_features[
        "ur3_speed_abs_mean"
    ]
    +
    stage_features[
        "ur5_speed_abs_mean"
    ]
)


stage_features[
    "combined_joint_path_per_sec"
] = (
    stage_features[
        "ur3_joint_path_per_sec"
    ]
    +
    stage_features[
        "ur5_joint_path_per_sec"
    ]
)


stage_features[
    "ur3_minus_ur5_speed"
] = (
    stage_features[
        "ur3_speed_abs_mean"
    ]
    -
    stage_features[
        "ur5_speed_abs_mean"
    ]
)


stage_features[
    "ur3_minus_ur5_path_rate"
] = (
    stage_features[
        "ur3_joint_path_per_sec"
    ]
    -
    stage_features[
        "ur5_joint_path_per_sec"
    ]
)


# =============================================================================
# 13. DEFINE PCA FEATURE CANDIDATES
# =============================================================================

# Context fields such as cycle_id, work_fixture, stage and timestamps are
# deliberately excluded from the PCA input.
#
# They remain available later for interpreting PCA scores.

PCA_FEATURES = [
    "stage_duration_sec",

    "ur3_speed_abs_mean",
    "ur3_speed_abs_std",
    "ur3_speed_abs_max",
    "ur3_joint_path_per_sec",
    "ur3_joint_net_change",
    "ur3_position_variability",

    "ur5_speed_abs_mean",
    "ur5_speed_abs_std",
    "ur5_speed_abs_max",
    "ur5_joint_path_per_sec",
    "ur5_joint_net_change",
    "ur5_position_variability",

    "combined_speed_abs_mean",
    "combined_joint_path_per_sec",

    "ur3_minus_ur5_speed",
    "ur3_minus_ur5_path_rate",
]


# =============================================================================
# 14. PCA FEATURE COMPLETENESS
# =============================================================================

print("\n" + "=" * 90)
print("PCA FEATURE COMPLETENESS")
print("=" * 90)


audit_rows = []


for feature in PCA_FEATURES:

    series = pd.to_numeric(
        stage_features[
            feature
        ],
        errors="coerce",
    )


    series = series.replace(
        [np.inf, -np.inf],
        np.nan,
    )


    audit_rows.append(
        {
            "feature":
                feature,

            "rows":
                len(series),

            "non_null":
                int(
                    series
                    .notna()
                    .sum()
                ),

            "missing":
                int(
                    series
                    .isna()
                    .sum()
                ),

            "missing_pct":
                (
                    series
                    .isna()
                    .mean()
                    * 100
                ),

            "unique_values":
                int(
                    series
                    .nunique(
                        dropna=True
                    )
                ),

            "mean":
                series.mean(),

            "std":
                series.std(),

            "min":
                series.min(),

            "max":
                series.max(),
        }
    )


feature_audit = pd.DataFrame(
    audit_rows
)


print(
    feature_audit
    .round(6)
    .to_string(
        index=False
    )
)


# =============================================================================
# 15. TELEMETRY COVERAGE BY STAGE
# =============================================================================

print("\n" + "=" * 90)
print("TELEMETRY COVERAGE BY STAGE")
print("=" * 90)


coverage = (
    stage_features
    .groupby(
        "stage",
        as_index=False,
        sort=False,
    )
    .agg(
        observations=(
            "cycle_id",
            "size",
        ),

        ur3_mean_samples=(
            "ur3_observations",
            "mean",
        ),

        ur5_mean_samples=(
            "ur5_observations",
            "mean",
        ),

        ur3_zero_sample_windows=(
            "ur3_observations",
            lambda x: int(
                (x == 0).sum()
            ),
        ),

        ur5_zero_sample_windows=(
            "ur5_observations",
            lambda x: int(
                (x == 0).sum()
            ),
        ),
    )
)


print(
    coverage
    .round(2)
    .to_string(
        index=False
    )
)


# =============================================================================
# 16. OVERALL TELEMETRY COVERAGE
# =============================================================================

ur3_available = (
    stage_features[
        "ur3_observations"
    ] > 0
)


ur5_available = (
    stage_features[
        "ur5_observations"
    ] > 0
)


both_available = (
    ur3_available
    & ur5_available
)


print("\n" + "=" * 90)
print("OVERALL DUAL-ROBOT COVERAGE")
print("=" * 90)


print(
    f"\nUR3 stages with telemetry: "
    f"{ur3_available.sum()} "
    f"({ur3_available.mean() * 100:.2f}%)"
)

print(
    f"UR5 stages with telemetry: "
    f"{ur5_available.sum()} "
    f"({ur5_available.mean() * 100:.2f}%)"
)

print(
    f"Both robots available:     "
    f"{both_available.sum()} "
    f"({both_available.mean() * 100:.2f}%)"
)


# =============================================================================
# 17. PCA FEATURE VARIABILITY
# =============================================================================

print("\n" + "=" * 90)
print("PCA FEATURE VARIABILITY")
print("=" * 90)


variability = (
    feature_audit[
        [
            "feature",
            "unique_values",
            "std",
            "min",
            "max",
        ]
    ]
    .copy()
)


variability[
    "range"
] = (
    variability[
        "max"
    ]
    - variability[
        "min"
    ]
)


print(
    variability
    .round(6)
    .to_string(
        index=False
    )
)


# =============================================================================
# 18. STAGE-LEVEL MOTION SUMMARY
# =============================================================================

print("\n" + "=" * 90)
print("STAGE-LEVEL MOTION SUMMARY")
print("=" * 90)


stage_summary = (
    stage_features
    .groupby(
        "stage",
        as_index=False,
        sort=False,
    )
    .agg(
        mean_duration_sec=(
            "stage_duration_sec",
            "mean",
        ),

        ur3_mean_speed=(
            "ur3_speed_abs_mean",
            "mean",
        ),

        ur5_mean_speed=(
            "ur5_speed_abs_mean",
            "mean",
        ),

        ur3_path_rate=(
            "ur3_joint_path_per_sec",
            "mean",
        ),

        ur5_path_rate=(
            "ur5_joint_path_per_sec",
            "mean",
        ),

        combined_speed=(
            "combined_speed_abs_mean",
            "mean",
        ),
    )
)


print(
    stage_summary
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 19. AGGREGATED FEATURE CORRELATION
# =============================================================================

print("\n" + "=" * 90)
print("AGGREGATED FEATURE CORRELATION")
print("=" * 90)


pca_data = (
    stage_features[
        PCA_FEATURES
    ]
    .apply(
        pd.to_numeric,
        errors="coerce",
    )
    .replace(
        [np.inf, -np.inf],
        np.nan,
    )
)


corr = pca_data.corr()


corr_rows = []


for i in range(
    len(PCA_FEATURES)
):

    for j in range(
        i + 1,
        len(PCA_FEATURES)
    ):

        f1 = PCA_FEATURES[i]
        f2 = PCA_FEATURES[j]

        value = corr.loc[
            f1,
            f2,
        ]

        if pd.notna(value):

            corr_rows.append(
                {
                    "feature_1":
                        f1,

                    "feature_2":
                        f2,

                    "correlation":
                        value,

                    "abs_correlation":
                        abs(value),
                }
            )


# Explicit columns ensure the DataFrame remains structurally valid even if
# no correlations can be calculated.

corr_pairs = pd.DataFrame(
    corr_rows,
    columns=[
        "feature_1",
        "feature_2",
        "correlation",
        "abs_correlation",
    ],
)


high_corr = (
    corr_pairs[
        corr_pairs[
            "abs_correlation"
        ] >= 0.80
    ]
    .sort_values(
        "abs_correlation",
        ascending=False,
    )
)


print(
    f"\nTotal PCA features: "
    f"{len(PCA_FEATURES)}"
)

print(
    f"Total calculable feature pairs: "
    f"{len(corr_pairs)}"
)

print(
    f"Pairs with |r| >= 0.80: "
    f"{len(high_corr)}"
)


if len(high_corr) > 0:

    print(
        "\nHighest correlations:"
    )

    print(
        high_corr[
            [
                "feature_1",
                "feature_2",
                "correlation",
            ]
        ]
        .head(20)
        .round(4)
        .to_string(
            index=False
        )
    )

else:

    print(
        "\nNo aggregated feature pairs "
        "exceeded |r| >= 0.80."
    )


# =============================================================================
# 20. COMPLETE-CASE PCA MATRIX
# =============================================================================

complete_mask = (
    pca_data
    .notna()
    .all(
        axis=1
    )
)


complete_rows = int(
    complete_mask.sum()
)


incomplete_rows = int(
    (~complete_mask).sum()
)


print("\n" + "=" * 90)
print("COMPLETE-CASE PCA MATRIX")
print("=" * 90)


print(
    f"\nTotal stage observations: "
    f"{len(stage_features)}"
)

print(
    f"Complete PCA observations: "
    f"{complete_rows}"
)

print(
    f"Incomplete PCA observations: "
    f"{incomplete_rows}"
)


if len(stage_features) > 0:

    print(
        f"Complete-case rate: "
        f"{complete_rows / len(stage_features) * 100:.2f}%"
    )


# =============================================================================
# 21. INCOMPLETE OBSERVATIONS BY STAGE
# =============================================================================

print("\n" + "=" * 90)
print("INCOMPLETE PCA OBSERVATIONS BY STAGE")
print("=" * 90)


stage_features[
    "pca_complete_case"
] = complete_mask


incomplete_by_stage = (
    stage_features
    .groupby(
        "stage",
        as_index=False,
        sort=False,
    )
    .agg(
        observations=(
            "cycle_id",
            "size",
        ),

        complete_cases=(
            "pca_complete_case",
            "sum",
        ),
    )
)


incomplete_by_stage[
    "incomplete_cases"
] = (
    incomplete_by_stage[
        "observations"
    ]
    - incomplete_by_stage[
        "complete_cases"
    ]
)


incomplete_by_stage[
    "complete_pct"
] = (
    incomplete_by_stage[
        "complete_cases"
    ]
    / incomplete_by_stage[
        "observations"
    ]
    * 100
)


print(
    incomplete_by_stage
    .round(2)
    .to_string(
        index=False
    )
)


# =============================================================================
# 22. SAVE FEATURE MATRIX
# =============================================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


stage_features.to_csv(
    OUTPUT_FILE,
    index=False,
)


print("\n" + "=" * 90)
print("OUTPUT")
print("=" * 90)


print(
    f"\nSaved:\n"
    f"{OUTPUT_FILE}"
)

print(
    f"\nOutput shape: "
    f"{stage_features.shape}"
)


# =============================================================================
# 23. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 90)
print("ANALYTICAL NOTE")
print("=" * 90)


print(
    """
This dataset changes the analytical unit from raw robot telemetry
samples to production process-stage observations.

Each row represents:

    one production cycle
    x
    one defined process stage

The process-stage duration is calculated from PartData event differences
using the validated /1e7 event-time scale.

Robot telemetry windows are NOT created from the absolute PartData event
timestamps.

Instead, the established clock bridge is used:

    UR3 event time
        =
    UR3TimePartAdded / 1e6
        +
    event offset from PartAdded / 1e7

and equivalently for UR5.

This reproduces the synchronization architecture established in the
earlier full-process alignment analysis.

The PCA candidate variables describe:

    - process-stage duration,
    - UR3 motion intensity and variability,
    - UR5 motion intensity and variability,
    - joint-position movement,
    - duration-normalized joint path,
    - relative dual-robot activity.

Identifiers, fixture labels, stage labels and timestamps are retained as
contextual variables but are not intended to enter PCA directly.

The next modelling step should use StandardScaler before PCA.

No missing-value imputation should be introduced automatically.

Very short stages, particularly t9_t10, may legitimately contain no PLC
telemetry samples because their duration is shorter than the telemetry
sampling interval. Their treatment must be decided from the observed
coverage before PCA is fitted.

PCA will only be retained if explained variance and component structure
show that dimensionality reduction provides a meaningful representation
of process-stage operating behaviour.

MLflow is still not required at this stage.
"""
)