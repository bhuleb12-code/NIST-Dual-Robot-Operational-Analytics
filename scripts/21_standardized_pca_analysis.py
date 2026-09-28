from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


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
    / "pca_process_stage_features.csv"
)

SCORES_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pca_process_stage_scores.csv"
)

LOADINGS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pca_component_loadings.csv"
)

VARIANCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pca_explained_variance.csv"
)


# =============================================================================
# 2. PCA FEATURE SET
# =============================================================================

# These are the underlying dual-robot physical motion features.
#
# Deliberately excluded:
#
# - stage_duration_sec:
#       retained as process context rather than allowing duration to define PCs
#
# - combined_speed_abs_mean:
#       mathematically derived from UR3 + UR5
#
# - combined_joint_path_per_sec:
#       mathematically derived from UR3 + UR5
#
# - ur3_minus_ur5_speed:
#       mathematically derived difference
#
# - ur3_minus_ur5_path_rate:
#       mathematically derived difference
#
# - cycle_id / stage / fixture / timestamps:
#       contextual variables, not continuous PCA inputs
#
# The objective is to determine whether the underlying robot-motion variables
# themselves can be represented by fewer latent operating-behaviour dimensions.

PCA_FEATURES = [
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
]


CONTEXT_COLUMNS = [
    "cycle_id",
    "work_fixture",
    "stage",
    "stage_duration_sec",
    "ur3_observations",
    "ur5_observations",
]


# =============================================================================
# 3. LOAD DATA
# =============================================================================

print("=" * 90)
print("NIST ROBOTIC WORK CELL - STANDARDIZED PCA ANALYSIS")
print("=" * 90)


if not INPUT_FILE.exists():

    raise FileNotFoundError(
        f"PCA feature matrix not found:\n"
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

required_columns = (
    PCA_FEATURES
    + CONTEXT_COLUMNS
)


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
# 5. PREPARE NUMERIC PCA MATRIX
# =============================================================================

X = (
    df[
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


complete_mask = (
    X
    .notna()
    .all(
        axis=1
    )
)


X_complete = (
    X.loc[
        complete_mask
    ]
    .copy()
)


context = (
    df.loc[
        complete_mask,
        CONTEXT_COLUMNS
    ]
    .copy()
)


print("\n" + "=" * 90)
print("PCA MODELLING POPULATION")
print("=" * 90)


print(
    f"\nTotal process-stage observations: "
    f"{len(df)}"
)

print(
    f"Complete PCA observations:       "
    f"{len(X_complete)}"
)

print(
    f"Excluded incomplete observations: "
    f"{len(df) - len(X_complete)}"
)

print(
    f"Retained percentage: "
    f"{len(X_complete) / len(df) * 100:.2f}%"
)


print(
    "\nComplete observations by stage:"
)


stage_counts = (
    context[
        "stage"
    ]
    .value_counts(
        sort=False
    )
    .rename_axis(
        "stage"
    )
    .reset_index(
        name="observations"
    )
)


print(
    stage_counts
    .to_string(
        index=False
    )
)


# =============================================================================
# 6. FEATURE SCALE BEFORE STANDARDIZATION
# =============================================================================

print("\n" + "=" * 90)
print("FEATURE SCALE BEFORE STANDARDIZATION")
print("=" * 90)


scale_summary = (
    X_complete
    .agg(
        [
            "mean",
            "std",
            "min",
            "max",
        ]
    )
    .T
)


scale_summary[
    "range"
] = (
    scale_summary[
        "max"
    ]
    - scale_summary[
        "min"
    ]
)


print(
    scale_summary
    .round(6)
    .to_string()
)


# =============================================================================
# 7. STANDARDIZE FEATURES
# =============================================================================

scaler = StandardScaler()


X_scaled = scaler.fit_transform(
    X_complete
)


scaled_means = (
    X_scaled.mean(
        axis=0
    )
)


scaled_stds = (
    X_scaled.std(
        axis=0,
        ddof=0,
    )
)


print("\n" + "=" * 90)
print("STANDARDIZATION CHECK")
print("=" * 90)


standardization_check = pd.DataFrame(
    {
        "feature":
            PCA_FEATURES,

        "scaled_mean":
            scaled_means,

        "scaled_std":
            scaled_stds,
    }
)


print(
    standardization_check
    .round(6)
    .to_string(
        index=False
    )
)


# =============================================================================
# 8. FIT FULL PCA
# =============================================================================

# We initially retain all possible components.
#
# We are not deciding the number of useful PCs in advance.
# Explained variance will make that decision evidence-based.

pca = PCA()


scores = pca.fit_transform(
    X_scaled
)


n_components = (
    pca.n_components_
)


component_names = [
    f"PC{i}"
    for i in range(
        1,
        n_components + 1
    )
]


# =============================================================================
# 9. EXPLAINED VARIANCE
# =============================================================================

explained_variance_ratio = (
    pca.explained_variance_ratio_
)


cumulative_variance = (
    np.cumsum(
        explained_variance_ratio
    )
)


variance_df = pd.DataFrame(
    {
        "component":
            component_names,

        "explained_variance_ratio":
            explained_variance_ratio,

        "explained_variance_pct":
            explained_variance_ratio
            * 100,

        "cumulative_variance_ratio":
            cumulative_variance,

        "cumulative_variance_pct":
            cumulative_variance
            * 100,

        "eigenvalue":
            pca.explained_variance_,
    }
)


print("\n" + "=" * 90)
print("PCA EXPLAINED VARIANCE")
print("=" * 90)


print(
    variance_df
    .round(6)
    .to_string(
        index=False
    )
)


# =============================================================================
# 10. COMPONENT COUNTS FOR COMMON VARIANCE THRESHOLDS
# =============================================================================

def components_for_threshold(
    cumulative,
    threshold,
):

    indices = np.where(
        cumulative >= threshold
    )[0]

    if len(indices) == 0:
        return len(cumulative)

    return int(
        indices[0] + 1
    )


threshold_rows = []


for threshold in [
    0.70,
    0.80,
    0.85,
    0.90,
    0.95,
]:

    component_count = (
        components_for_threshold(
            cumulative_variance,
            threshold,
        )
    )

    threshold_rows.append(
        {
            "variance_target_pct":
                threshold * 100,

            "components_required":
                component_count,

            "actual_cumulative_pct":
                cumulative_variance[
                    component_count - 1
                ]
                * 100,
        }
    )


threshold_df = pd.DataFrame(
    threshold_rows
)


print("\n" + "=" * 90)
print("COMPONENTS REQUIRED BY VARIANCE TARGET")
print("=" * 90)


print(
    threshold_df
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 11. KAISER CRITERION
# =============================================================================

# Because PCA is fitted to standardized features, each original feature has
# variance approximately 1.
#
# The Kaiser criterion therefore considers PCs with eigenvalue > 1 as a useful
# descriptive reference.
#
# It is NOT treated as an automatic model-selection rule.

kaiser_components = int(
    (
        pca.explained_variance_
        > 1.0
    )
    .sum()
)


print("\n" + "=" * 90)
print("KAISER CRITERION - DESCRIPTIVE ONLY")
print("=" * 90)


print(
    f"\nComponents with eigenvalue > 1: "
    f"{kaiser_components}"
)


if kaiser_components > 0:

    print(
        f"Cumulative variance at that point: "
        f"{cumulative_variance[kaiser_components - 1] * 100:.2f}%"
    )


# =============================================================================
# 12. PCA LOADINGS
# =============================================================================

# Rows = original physical features
# Columns = principal components

loadings = pd.DataFrame(
    pca.components_.T,
    index=PCA_FEATURES,
    columns=component_names,
)


print("\n" + "=" * 90)
print("PCA LOADINGS")
print("=" * 90)


# Print the first six components for readability.
display_components = component_names[
    :min(
        6,
        len(component_names),
    )
]


print(
    loadings[
        display_components
    ]
    .round(4)
    .to_string()
)


# =============================================================================
# 13. DOMINANT FEATURES BY COMPONENT
# =============================================================================

print("\n" + "=" * 90)
print("DOMINANT FEATURES BY COMPONENT")
print("=" * 90)


dominant_rows = []


for component in display_components:

    component_loadings = (
        loadings[
            component
        ]
        .copy()
    )


    ordered_features = (
        component_loadings
        .abs()
        .sort_values(
            ascending=False
        )
        .index
    )


    for rank, feature in enumerate(
        ordered_features[
            :5
        ],
        start=1,
    ):

        dominant_rows.append(
            {
                "component":
                    component,

                "rank":
                    rank,

                "feature":
                    feature,

                "loading":
                    component_loadings[
                        feature
                    ],

                "abs_loading":
                    abs(
                        component_loadings[
                            feature
                        ]
                    ),
            }
        )


dominant_df = pd.DataFrame(
    dominant_rows
)


print(
    dominant_df
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 14. PCA SCORES
# =============================================================================

scores_df = pd.DataFrame(
    scores,
    columns=component_names,
    index=X_complete.index,
)


scores_output = pd.concat(
    [
        context,
        scores_df,
    ],
    axis=1,
)


print("\n" + "=" * 90)
print("PCA SCORE SUMMARY")
print("=" * 90)


print(
    scores_df[
        component_names[
            :min(
                6,
                len(component_names),
            )
        ]
    ]
    .describe()
    .round(4)
    .to_string()
)


# =============================================================================
# 15. PCA SCORES BY PROCESS STAGE
# =============================================================================

print("\n" + "=" * 90)
print("MEAN PCA SCORES BY PROCESS STAGE")
print("=" * 90)


stage_score_components = (
    component_names[
        :min(
            4,
            len(component_names),
        )
    ]
)


stage_score_summary = (
    scores_output
    .groupby(
        "stage",
        as_index=False,
        sort=False,
    )[
        stage_score_components
    ]
    .mean()
)


print(
    stage_score_summary
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 16. PCA SCORES BY WORK FIXTURE
# =============================================================================

print("\n" + "=" * 90)
print("MEAN PCA SCORES BY WORK FIXTURE")
print("=" * 90)


fixture_score_summary = (
    scores_output
    .groupby(
        "work_fixture",
        as_index=False,
    )[
        stage_score_components
    ]
    .mean()
)


print(
    fixture_score_summary
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 17. RELATIONSHIP BETWEEN PCs AND STAGE DURATION
# =============================================================================

print("\n" + "=" * 90)
print("PCA SCORE RELATIONSHIP WITH STAGE DURATION")
print("=" * 90)


duration_correlations = []


for component in component_names:

    correlation = (
        scores_output[
            component
        ]
        .corr(
            scores_output[
                "stage_duration_sec"
            ]
        )
    )


    duration_correlations.append(
        {
            "component":
                component,

            "correlation_with_stage_duration":
                correlation,

            "abs_correlation":
                abs(
                    correlation
                )
                if pd.notna(correlation)
                else np.nan,
        }
    )


duration_corr_df = (
    pd.DataFrame(
        duration_correlations
    )
    .sort_values(
        "abs_correlation",
        ascending=False,
    )
)


print(
    duration_corr_df
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 18. RECONSTRUCTION ERROR
# =============================================================================

# Reconstruction error is calculated here only as a descriptive PCA diagnostic.
#
# We are NOT declaring high reconstruction-error observations to be anomalies.

reconstruction_rows = []


for component_count in sorted(
    set(
        [
            2,
            3,
            4,
            components_for_threshold(
                cumulative_variance,
                0.80,
            ),
            components_for_threshold(
                cumulative_variance,
                0.90,
            ),
        ]
    )
):

    if component_count > n_components:
        continue


    reduced_scores = (
        scores[
            :,
            :component_count
        ]
    )


    reconstructed = (
        reduced_scores
        @ pca.components_[
            :component_count,
            :
        ]
    )


    mse_per_row = (
        (
            X_scaled
            - reconstructed
        )
        ** 2
    ).mean(
        axis=1
    )


    reconstruction_rows.append(
        {
            "components":
                component_count,

            "mean_reconstruction_mse":
                mse_per_row.mean(),

            "median_reconstruction_mse":
                np.median(
                    mse_per_row
                ),

            "p95_reconstruction_mse":
                np.quantile(
                    mse_per_row,
                    0.95,
                ),
        }
    )


reconstruction_df = pd.DataFrame(
    reconstruction_rows
)


print("\n" + "=" * 90)
print("PCA RECONSTRUCTION DIAGNOSTIC")
print("=" * 90)


print(
    reconstruction_df
    .round(6)
    .to_string(
        index=False
    )
)


# =============================================================================
# 19. SAVE OUTPUTS
# =============================================================================

SCORES_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


scores_output.to_csv(
    SCORES_FILE,
    index=False,
)


loadings.reset_index(
    names="feature"
).to_csv(
    LOADINGS_FILE,
    index=False,
)


variance_df.to_csv(
    VARIANCE_FILE,
    index=False,
)


print("\n" + "=" * 90)
print("OUTPUTS")
print("=" * 90)


print(
    f"\nPCA scores:\n"
    f"{SCORES_FILE}"
)

print(
    f"\nPCA loadings:\n"
    f"{LOADINGS_FILE}"
)

print(
    f"\nExplained variance:\n"
    f"{VARIANCE_FILE}"
)


print(
    f"\nScores shape:   "
    f"{scores_output.shape}"
)

print(
    f"Loadings shape: "
    f"{loadings.shape}"
)

print(
    f"Variance shape: "
    f"{variance_df.shape}"
)


# =============================================================================
# 20. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 90)
print("ANALYTICAL NOTE")
print("=" * 90)


print(
    """
This PCA is fitted to standardized underlying dual-robot motion features.

The PCA does NOT include:

    - cycle identifiers,
    - process-stage labels,
    - work-fixture identifiers,
    - timestamps,
    - observation counts,
    - stage duration,
    - mathematically derived UR3/UR5 sums or differences.

Stage duration, process stage and work fixture are retained as contextual
variables for interpreting the resulting principal-component scores.

Incomplete observations are excluded rather than imputed. The dominant
source of incompleteness is the t9_t10 stage, whose duration is shorter
than the PLC telemetry sampling interval.

PCA is being used here as an exploratory representation of multivariate
dual-robot operating behaviour.

A principal component is not automatically a physical machine state,
failure mode or bottleneck. Component interpretation must come from its
loadings and its relationship with independently defined process context.

Explained variance will determine whether PCA provides useful dimensionality
reduction. No component count is accepted merely because PCA was requested.

The Kaiser criterion is reported only as a descriptive reference.

Reconstruction error is also diagnostic at this stage and must not be
labelled as anomaly or failure evidence.

MLflow remains unnecessary until there are multiple legitimate modelling
experiments or parameterized anomaly-detection runs worth tracking.
"""
)