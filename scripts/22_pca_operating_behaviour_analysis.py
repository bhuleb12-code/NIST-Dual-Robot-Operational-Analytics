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

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pca_process_stage_scores.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pca_within_stage_deviation.csv"
)

SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pca_within_stage_deviation_summary.csv"
)


# =============================================================================
# 2. CONFIGURATION
# =============================================================================

# Script 21 showed:
#
# PC1 = 55.48%
# PC2 = 24.16%
# PC3 =  7.09%
# PC4 =  6.27%
#
# Cumulative variance = approximately 93.0%.
#
# We therefore retain PC1-PC4 for the operating-behaviour representation.

PC_COLUMNS = [
    "PC1",
    "PC2",
    "PC3",
    "PC4",
]


# This analysis does NOT declare failures.
#
# We rank observations by their multivariate distance from the normal centre
# of their OWN process stage.
#
# A 95th-percentile threshold is used only as an exploratory high-deviation
# flag. It is not a learned failure threshold.

DEVIATION_QUANTILE = 0.95


# =============================================================================
# 3. LOAD DATA
# =============================================================================

print("=" * 90)
print("NIST ROBOTIC WORK CELL - WITHIN-STAGE PCA OPERATING-BEHAVIOUR ANALYSIS")
print("=" * 90)


if not INPUT_FILE.exists():

    raise FileNotFoundError(
        f"PCA score file not found:\n"
        f"{INPUT_FILE}"
    )


df = pd.read_csv(
    INPUT_FILE
)


print(
    f"\nInput shape: "
    f"{df.shape}"
)


# =============================================================================
# 4. VALIDATE REQUIRED COLUMNS
# =============================================================================

required_columns = [
    "cycle_id",
    "work_fixture",
    "stage",
    "stage_duration_sec",
    "ur3_observations",
    "ur5_observations",
] + PC_COLUMNS


missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]


if missing_columns:

    raise ValueError(
        "Required columns missing:\n"
        f"{missing_columns}"
    )


# =============================================================================
# 5. NUMERIC PREPARATION
# =============================================================================

numeric_columns = [
    "cycle_id",
    "work_fixture",
    "stage_duration_sec",
    "ur3_observations",
    "ur5_observations",
] + PC_COLUMNS


for column in numeric_columns:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    )


df = df.replace(
    [np.inf, -np.inf],
    np.nan,
)


valid_mask = (
    df[
        PC_COLUMNS
    ]
    .notna()
    .all(
        axis=1
    )
    &
    df[
        "stage"
    ]
    .notna()
)


analysis = (
    df.loc[
        valid_mask
    ]
    .copy()
    .reset_index(
        drop=True
    )
)


print("\n" + "=" * 90)
print("ANALYTICAL POPULATION")
print("=" * 90)


print(
    f"\nValid PCA observations: "
    f"{len(analysis)}"
)

print(
    f"Cycles represented: "
    f"{analysis['cycle_id'].nunique()}"
)

print(
    f"Stages represented: "
    f"{analysis['stage'].nunique()}"
)


# =============================================================================
# 6. STAGE COUNTS
# =============================================================================

print("\n" + "=" * 90)
print("OBSERVATIONS BY PROCESS STAGE")
print("=" * 90)


stage_counts = (
    analysis
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

        cycles=(
            "cycle_id",
            "nunique",
        ),
    )
)


print(
    stage_counts
    .to_string(
        index=False
    )
)


# =============================================================================
# 7. WITHIN-STAGE PCA STANDARDIZATION
# =============================================================================

# PCA scores have different centres across process stages.
#
# Therefore, for each PC:
#
#     within-stage z-score
#         =
#     (observation PC score - stage mean)
#         /
#     stage standard deviation
#
# This asks:
#
# "How unusual is this observation compared with other observations
#  performing the same process stage?"
#
# It does NOT compare t3_t4 directly against t8_t9, for example.


print("\n" + "=" * 90)
print("WITHIN-STAGE PCA STANDARDIZATION")
print("=" * 90)


for pc in PC_COLUMNS:

    stage_mean = (
        analysis
        .groupby(
            "stage"
        )[pc]
        .transform(
            "mean"
        )
    )


    stage_std = (
        analysis
        .groupby(
            "stage"
        )[pc]
        .transform(
            "std"
        )
    )


    # Protect against zero stage-level variance.
    stage_std = stage_std.replace(
        0,
        np.nan,
    )


    analysis[
        f"{pc}_stage_mean"
    ] = stage_mean


    analysis[
        f"{pc}_stage_std"
    ] = stage_std


    analysis[
        f"{pc}_within_stage_z"
    ] = (
        (
            analysis[pc]
            - stage_mean
        )
        /
        stage_std
    )


z_columns = [
    f"{pc}_within_stage_z"
    for pc in PC_COLUMNS
]


# =============================================================================
# 8. CHECK WITHIN-STAGE STANDARDIZATION
# =============================================================================

z_check_rows = []


for stage, group in analysis.groupby(
    "stage",
    sort=False,
):

    row = {
        "stage":
            stage,

        "observations":
            len(group),
    }


    for pc in PC_COLUMNS:

        z_col = (
            f"{pc}_within_stage_z"
        )

        row[
            f"{pc}_z_mean"
        ] = (
            group[
                z_col
            ]
            .mean()
        )

        row[
            f"{pc}_z_std"
        ] = (
            group[
                z_col
            ]
            .std()
        )


    z_check_rows.append(
        row
    )


z_check = pd.DataFrame(
    z_check_rows
)


print(
    z_check
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 9. MULTIVARIATE WITHIN-STAGE DEVIATION DISTANCE
# =============================================================================

# Euclidean distance in the four-dimensional within-stage standardized
# PCA space.
#
# A larger value means the observation is farther from the typical
# multivariate operating pattern for its own stage.
#
# This is a descriptive deviation score, not a probability of failure.

analysis[
    "within_stage_pca_distance"
] = np.sqrt(
    (
        analysis[
            z_columns
        ]
        ** 2
    )
    .sum(
        axis=1
    )
)


# =============================================================================
# 10. GLOBAL EXPLORATORY DEVIATION THRESHOLD
# =============================================================================

global_threshold = (
    analysis[
        "within_stage_pca_distance"
    ]
    .quantile(
        DEVIATION_QUANTILE
    )
)


analysis[
    "global_high_deviation"
] = (
    analysis[
        "within_stage_pca_distance"
    ]
    >= global_threshold
)


print("\n" + "=" * 90)
print("GLOBAL EXPLORATORY DEVIATION THRESHOLD")
print("=" * 90)


print(
    f"\nQuantile: "
    f"{DEVIATION_QUANTILE:.2f}"
)

print(
    f"Distance threshold: "
    f"{global_threshold:.4f}"
)

print(
    f"High-deviation observations: "
    f"{analysis['global_high_deviation'].sum()}"
)

print(
    f"High-deviation rate: "
    f"{analysis['global_high_deviation'].mean() * 100:.2f}%"
)


# =============================================================================
# 11. STAGE-SPECIFIC EXPLORATORY THRESHOLDS
# =============================================================================

# We also calculate each stage's own 95th-percentile distance.
#
# This prevents a naturally more variable stage from dominating the global
# high-deviation set.


stage_thresholds = (
    analysis
    .groupby(
        "stage"
    )[
        "within_stage_pca_distance"
    ]
    .transform(
        lambda x:
            x.quantile(
                DEVIATION_QUANTILE
            )
    )
)


analysis[
    "stage_distance_threshold"
] = stage_thresholds


analysis[
    "stage_high_deviation"
] = (
    analysis[
        "within_stage_pca_distance"
    ]
    >= analysis[
        "stage_distance_threshold"
    ]
)


# =============================================================================
# 12. DEVIATION SUMMARY BY STAGE
# =============================================================================

print("\n" + "=" * 90)
print("DEVIATION SUMMARY BY PROCESS STAGE")
print("=" * 90)


stage_summary = (
    analysis
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

        mean_distance=(
            "within_stage_pca_distance",
            "mean",
        ),

        median_distance=(
            "within_stage_pca_distance",
            "median",
        ),

        p95_distance=(
            "within_stage_pca_distance",
            lambda x:
                x.quantile(
                    0.95
                ),
        ),

        max_distance=(
            "within_stage_pca_distance",
            "max",
        ),

        global_high_deviation_count=(
            "global_high_deviation",
            "sum",
        ),

        stage_high_deviation_count=(
            "stage_high_deviation",
            "sum",
        ),
    )
)


stage_summary[
    "global_high_deviation_pct"
] = (
    stage_summary[
        "global_high_deviation_count"
    ]
    /
    stage_summary[
        "observations"
    ]
    * 100
)


stage_summary[
    "stage_high_deviation_pct"
] = (
    stage_summary[
        "stage_high_deviation_count"
    ]
    /
    stage_summary[
        "observations"
    ]
    * 100
)


print(
    stage_summary
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 13. TOP DEVIATION OBSERVATIONS
# =============================================================================

print("\n" + "=" * 90)
print("TOP 25 WITHIN-STAGE PCA DEVIATIONS")
print("=" * 90)


top_deviations = (
    analysis
    .sort_values(
        "within_stage_pca_distance",
        ascending=False,
    )
    [
        [
            "cycle_id",
            "work_fixture",
            "stage",
            "stage_duration_sec",
            "PC1",
            "PC2",
            "PC3",
            "PC4",
            "within_stage_pca_distance",
            "global_high_deviation",
            "stage_high_deviation",
        ]
    ]
    .head(
        25
    )
)


print(
    top_deviations
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 14. DEVIATION BY WORK FIXTURE
# =============================================================================

print("\n" + "=" * 90)
print("DEVIATION SUMMARY BY WORK FIXTURE")
print("=" * 90)


fixture_summary = (
    analysis
    .groupby(
        "work_fixture",
        as_index=False,
    )
    .agg(
        observations=(
            "cycle_id",
            "size",
        ),

        mean_distance=(
            "within_stage_pca_distance",
            "mean",
        ),

        median_distance=(
            "within_stage_pca_distance",
            "median",
        ),

        high_deviation_count=(
            "stage_high_deviation",
            "sum",
        ),
    )
)


fixture_summary[
    "high_deviation_pct"
] = (
    fixture_summary[
        "high_deviation_count"
    ]
    /
    fixture_summary[
        "observations"
    ]
    * 100
)


print(
    fixture_summary
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 15. RELATIONSHIP WITH STAGE DURATION
# =============================================================================

# Because stage identity has already been controlled in the PCA deviation
# calculation, we can now ask whether unusually different robot behaviour
# within a stage tends to accompany unusually long/short stage duration.


analysis[
    "stage_duration_mean"
] = (
    analysis
    .groupby(
        "stage"
    )[
        "stage_duration_sec"
    ]
    .transform(
        "mean"
    )
)


analysis[
    "stage_duration_std"
] = (
    analysis
    .groupby(
        "stage"
    )[
        "stage_duration_sec"
    ]
    .transform(
        "std"
    )
)


analysis[
    "stage_duration_std"
] = (
    analysis[
        "stage_duration_std"
    ]
    .replace(
        0,
        np.nan,
    )
)


analysis[
    "stage_duration_z"
] = (
    (
        analysis[
            "stage_duration_sec"
        ]
        - analysis[
            "stage_duration_mean"
        ]
    )
    /
    analysis[
        "stage_duration_std"
    ]
)


analysis[
    "stage_duration_abs_z"
] = (
    analysis[
        "stage_duration_z"
    ]
    .abs()
)


distance_duration_corr = (
    analysis[
        "within_stage_pca_distance"
    ]
    .corr(
        analysis[
            "stage_duration_abs_z"
        ]
    )
)


print("\n" + "=" * 90)
print("DEVIATION RELATIONSHIP WITH WITHIN-STAGE DURATION VARIATION")
print("=" * 90)


print(
    f"\nCorrelation between PCA deviation distance "
    f"and absolute within-stage duration z-score: "
    f"{distance_duration_corr:.4f}"
)


# =============================================================================
# 16. HIGH-DEVIATION VS OTHER OBSERVATIONS
# =============================================================================

print("\n" + "=" * 90)
print("HIGH-DEVIATION VS OTHER OBSERVATIONS")
print("=" * 90)


comparison = (
    analysis
    .groupby(
        "stage_high_deviation",
        as_index=False,
    )
    .agg(
        observations=(
            "cycle_id",
            "size",
        ),

        mean_pca_distance=(
            "within_stage_pca_distance",
            "mean",
        ),

        mean_abs_duration_z=(
            "stage_duration_abs_z",
            "mean",
        ),

        median_abs_duration_z=(
            "stage_duration_abs_z",
            "median",
        ),

        mean_stage_duration_sec=(
            "stage_duration_sec",
            "mean",
        ),
    )
)


print(
    comparison
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 17. CYCLE-LEVEL DEVIATION CONCENTRATION
# =============================================================================

# A cycle may contain several process stages.
#
# Count how many stage-specific high-deviation observations occur within
# each production cycle.

cycle_summary = (
    analysis
    .groupby(
        "cycle_id",
        as_index=False,
    )
    .agg(
        stages_observed=(
            "stage",
            "size",
        ),

        high_deviation_stages=(
            "stage_high_deviation",
            "sum",
        ),

        mean_pca_distance=(
            "within_stage_pca_distance",
            "mean",
        ),

        max_pca_distance=(
            "within_stage_pca_distance",
            "max",
        ),

        mean_abs_duration_z=(
            "stage_duration_abs_z",
            "mean",
        ),

        max_abs_duration_z=(
            "stage_duration_abs_z",
            "max",
        ),
    )
)


cycle_summary = (
    cycle_summary
    .sort_values(
        [
            "high_deviation_stages",
            "max_pca_distance",
        ],
        ascending=[
            False,
            False,
        ],
    )
)


print("\n" + "=" * 90)
print("TOP CYCLES BY DEVIATION CONCENTRATION")
print("=" * 90)


print(
    cycle_summary
    .head(
        20
    )
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 18. CHECK STARTUP / CENTRAL / RUNOUT LOCATION
# =============================================================================

# Earlier production analysis identified:
#
# cycles 1-5   = startup / pipeline-fill region
# cycles 6-55  = central steady-state region
# cycles 56-60 = runout region
#
# We do not assume startup/runout observations are abnormal.
# We simply check where the deviation flags occur.


def cycle_region(
    cycle_id,
):

    if cycle_id <= 5:
        return "startup_1_5"

    if cycle_id >= 56:
        return "runout_56_60"

    return "central_6_55"


analysis[
    "cycle_region"
] = (
    analysis[
        "cycle_id"
    ]
    .apply(
        cycle_region
    )
)


region_summary = (
    analysis
    .groupby(
        "cycle_region",
        as_index=False,
    )
    .agg(
        observations=(
            "cycle_id",
            "size",
        ),

        mean_distance=(
            "within_stage_pca_distance",
            "mean",
        ),

        stage_high_deviation_count=(
            "stage_high_deviation",
            "sum",
        ),
    )
)


region_summary[
    "stage_high_deviation_pct"
] = (
    region_summary[
        "stage_high_deviation_count"
    ]
    /
    region_summary[
        "observations"
    ]
    * 100
)


print("\n" + "=" * 90)
print("DEVIATION BY PRODUCTION REGION")
print("=" * 90)


print(
    region_summary
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 19. SAVE OUTPUTS
# =============================================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


analysis.to_csv(
    OUTPUT_FILE,
    index=False,
)


stage_summary.to_csv(
    SUMMARY_FILE,
    index=False,
)


print("\n" + "=" * 90)
print("OUTPUTS")
print("=" * 90)


print(
    f"\nObservation-level deviation file:\n"
    f"{OUTPUT_FILE}"
)

print(
    f"\nStage-level summary file:\n"
    f"{SUMMARY_FILE}"
)

print(
    f"\nObservation output shape: "
    f"{analysis.shape}"
)

print(
    f"Stage summary shape: "
    f"{stage_summary.shape}"
)


# =============================================================================
# 20. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 90)
print("ANALYTICAL NOTE")
print("=" * 90)


print(
    """
This analysis evaluates multivariate robot operating behaviour relative to
the normal behaviour of the SAME process stage.

This is important because the PCA analysis showed that normal process stages
occupy substantially different regions of PCA space. A global distance from
the overall PCA centre would therefore risk treating legitimate stage-specific
robot behaviour as abnormal.

The first four principal components are retained because they represent
approximately 93% of the variance in the twelve standardized dual-robot
motion features.

For each process stage, PC1-PC4 are standardized relative to that stage's
own mean and standard deviation. Euclidean distance in this four-dimensional
within-stage standardized space is then used as a descriptive multivariate
deviation score.

The 95th-percentile flags are exploratory ranking devices. They do NOT mean:

    - failure,
    - fault,
    - unsafe operation,
    - predictive maintenance event,
    - causal bottleneck,
    - statistically proven abnormality.

No labelled failure outcome exists in this dataset for validating such claims.

The analysis also checks whether large robot-behaviour deviations correspond
with unusual process-stage duration. Any relationship is descriptive and does
not establish causality.

Startup and runout cycles are retained and explicitly labelled because their
operating context differs from the central steady-state production region.

The purpose of this layer is condition-monitoring-style operational context:
identify observations whose multivariate robot behaviour differs substantially
from the usual behaviour observed for the same process stage.

Isolation Forest and MLflow should only be considered after these results are
inspected. If this simpler stage-aware PCA representation already provides
clear and stable operational information, additional modelling complexity may
not be justified.
"""
)