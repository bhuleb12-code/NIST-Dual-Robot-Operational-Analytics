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
    / "pca_suitability_analysis.csv"
)


# =============================================================================
# 2. LOAD DATA
# =============================================================================

print("=" * 90)
print("NIST ROBOTIC WORK CELL - PCA SUITABILITY ANALYSIS")
print("=" * 90)


def load_required_csv(path, label):

    if not path.exists():
        raise FileNotFoundError(
            f"{label} not found:\n{path}"
        )

    df = pd.read_csv(path)

    print(
        f"{label:<25} "
        f"shape={df.shape}"
    )

    return df


ur3 = load_required_csv(
    UR3_FILE,
    "UR3 operational features",
)

ur5 = load_required_csv(
    UR5_FILE,
    "UR5 operational features",
)


# =============================================================================
# 3. DISPLAY AVAILABLE COLUMNS
# =============================================================================

print("\n" + "=" * 90)
print("AVAILABLE FEATURES")
print("=" * 90)

print("\nUR3 columns:")
for col in ur3.columns:
    print(f"  {col}")

print("\nUR5 columns:")
for col in ur5.columns:
    print(f"  {col}")


# =============================================================================
# 4. IDENTIFY CORE JOINT SIGNALS
# =============================================================================

# We deliberately begin with physical joint-position and joint-velocity
# measurements.
#
# PCA should initially represent robot motion itself rather than a mixture
# of timestamps, identifiers, manually derived summary statistics and
# physical signals.

position_features = [
    f"j{i}_qactual"
    for i in range(1, 7)
]

velocity_features = [
    f"j{i}_qdactual"
    for i in range(1, 7)
]

candidate_features = (
    position_features
    + velocity_features
)


def existing_features(df, candidates):

    return [
        col
        for col in candidates
        if col in df.columns
    ]


ur3_features = existing_features(
    ur3,
    candidate_features,
)

ur5_features = existing_features(
    ur5,
    candidate_features,
)


print("\n" + "=" * 90)
print("INITIAL PCA CANDIDATE FEATURES")
print("=" * 90)

print(
    f"\nExpected candidate signals: "
    f"{len(candidate_features)}"
)

print(
    f"UR3 candidate signals found: "
    f"{len(ur3_features)}"
)

print(
    f"UR5 candidate signals found: "
    f"{len(ur5_features)}"
)

print("\nUR3:")
for col in ur3_features:
    print(f"  {col}")

print("\nUR5:")
for col in ur5_features:
    print(f"  {col}")


if len(ur3_features) == 0:
    raise ValueError(
        "No expected UR3 joint signals were found."
    )

if len(ur5_features) == 0:
    raise ValueError(
        "No expected UR5 joint signals were found."
    )


# =============================================================================
# 5. BASIC FEATURE QUALITY AUDIT
# =============================================================================

def feature_audit(df, features, robot):

    rows = []

    for col in features:

        series = pd.to_numeric(
            df[col],
            errors="coerce",
        )

        finite = series.replace(
            [np.inf, -np.inf],
            np.nan,
        )

        rows.append(
            {
                "robot": robot,
                "feature": col,
                "rows": len(series),
                "non_null": int(
                    finite.notna().sum()
                ),
                "missing": int(
                    finite.isna().sum()
                ),
                "missing_pct": (
                    finite.isna().mean()
                    * 100
                ),
                "unique_values": int(
                    finite.nunique(
                        dropna=True
                    )
                ),
                "mean": finite.mean(),
                "std": finite.std(),
                "min": finite.min(),
                "max": finite.max(),
                "range": (
                    finite.max()
                    - finite.min()
                ),
            }
        )

    return pd.DataFrame(rows)


audit = pd.concat(
    [
        feature_audit(
            ur3,
            ur3_features,
            "UR3",
        ),
        feature_audit(
            ur5,
            ur5_features,
            "UR5",
        ),
    ],
    ignore_index=True,
)


print("\n" + "=" * 90)
print("FEATURE QUALITY AUDIT")
print("=" * 90)

print(
    audit.round(6).to_string(
        index=False
    )
)


# =============================================================================
# 6. CONSTANT / NEAR-CONSTANT FEATURE CHECK
# =============================================================================

audit[
    "constant_feature"
] = (
    audit[
        "unique_values"
    ]
    <= 1
)

# A near-zero standard deviation signal contributes almost no useful
# variance to PCA.

audit[
    "near_constant_feature"
] = (
    audit[
        "std"
    ]
    .fillna(0)
    < 1e-8
)


print("\n" + "=" * 90)
print("CONSTANT / NEAR-CONSTANT CHECK")
print("=" * 90)

constant_check = audit[
    [
        "robot",
        "feature",
        "unique_values",
        "std",
        "constant_feature",
        "near_constant_feature",
    ]
]

print(
    constant_check.round(8).to_string(
        index=False
    )
)


# =============================================================================
# 7. CORRELATION / REDUNDANCY ANALYSIS
# =============================================================================

def correlation_analysis(
    df,
    features,
    robot,
    threshold=0.80,
):

    numeric = (
        df[features]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
    )

    corr = numeric.corr()

    rows = []

    for i in range(
        len(features)
    ):

        for j in range(
            i + 1,
            len(features)
        ):

            f1 = features[i]
            f2 = features[j]

            value = corr.loc[
                f1,
                f2,
            ]

            if pd.notna(value):

                rows.append(
                    {
                        "robot": robot,
                        "feature_1": f1,
                        "feature_2": f2,
                        "correlation": value,
                        "abs_correlation": abs(
                            value
                        ),
                        "high_correlation": (
                            abs(value)
                            >= threshold
                        ),
                    }
                )

    return pd.DataFrame(rows)


ur3_corr = correlation_analysis(
    ur3,
    ur3_features,
    "UR3",
)

ur5_corr = correlation_analysis(
    ur5,
    ur5_features,
    "UR5",
)

correlations = pd.concat(
    [
        ur3_corr,
        ur5_corr,
    ],
    ignore_index=True,
)


print("\n" + "=" * 90)
print("HIGH-CORRELATION FEATURE PAIRS |r| >= 0.80")
print("=" * 90)

high_corr = correlations[
    correlations[
        "high_correlation"
    ]
].copy()

high_corr = high_corr.sort_values(
    [
        "robot",
        "abs_correlation",
    ],
    ascending=[
        True,
        False,
    ],
)

if high_corr.empty:

    print(
        "\nNo feature pairs exceeded "
        "|r| >= 0.80."
    )

else:

    print(
        high_corr[
            [
                "robot",
                "feature_1",
                "feature_2",
                "correlation",
            ]
        ]
        .round(4)
        .to_string(
            index=False
        )
    )


# =============================================================================
# 8. CORRELATION SUMMARY
# =============================================================================

print("\n" + "=" * 90)
print("CORRELATION SUMMARY")
print("=" * 90)

summary_rows = []

for robot, corr_df in [
    ("UR3", ur3_corr),
    ("UR5", ur5_corr),
]:

    total_pairs = len(
        corr_df
    )

    high_pairs = int(
        corr_df[
            "high_correlation"
        ].sum()
    )

    mean_abs_corr = (
        corr_df[
            "abs_correlation"
        ].mean()
    )

    median_abs_corr = (
        corr_df[
            "abs_correlation"
        ].median()
    )

    max_abs_corr = (
        corr_df[
            "abs_correlation"
        ].max()
    )

    high_pct = (
        high_pairs
        / total_pairs
        * 100
        if total_pairs
        else np.nan
    )

    summary_rows.append(
        {
            "robot": robot,
            "feature_count": (
                len(ur3_features)
                if robot == "UR3"
                else len(ur5_features)
            ),
            "feature_pairs": total_pairs,
            "high_corr_pairs": high_pairs,
            "high_corr_pair_pct": high_pct,
            "mean_abs_correlation": mean_abs_corr,
            "median_abs_correlation": median_abs_corr,
            "max_abs_correlation": max_abs_corr,
        }
    )


corr_summary = pd.DataFrame(
    summary_rows
)

print(
    corr_summary.round(4).to_string(
        index=False
    )
)


# =============================================================================
# 9. POSITION VS VELOCITY REDUNDANCY
# =============================================================================

print("\n" + "=" * 90)
print("SIGNAL-GROUP SUMMARY")
print("=" * 90)

group_rows = []

for robot, df, features in [
    (
        "UR3",
        ur3,
        ur3_features,
    ),
    (
        "UR5",
        ur5,
        ur5_features,
    ),
]:

    for group_name, group_candidates in [
        (
            "joint_position",
            position_features,
        ),
        (
            "joint_velocity",
            velocity_features,
        ),
    ]:

        group_features = [
            col
            for col in group_candidates
            if col in features
        ]

        if not group_features:
            continue

        group_data = (
            df[group_features]
            .apply(
                pd.to_numeric,
                errors="coerce",
            )
        )

        group_rows.append(
            {
                "robot": robot,
                "signal_group": group_name,
                "feature_count": len(
                    group_features
                ),
                "mean_feature_std": (
                    group_data.std().mean()
                ),
                "mean_feature_range": (
                    (
                        group_data.max()
                        - group_data.min()
                    ).mean()
                ),
            }
        )


group_summary = pd.DataFrame(
    group_rows
)

print(
    group_summary.round(6).to_string(
        index=False
    )
)


# =============================================================================
# 10. SCALE DIFFERENCE CHECK
# =============================================================================

print("\n" + "=" * 90)
print("FEATURE SCALE CHECK")
print("=" * 90)

for robot in [
    "UR3",
    "UR5",
]:

    robot_audit = audit[
        audit[
            "robot"
        ] == robot
    ]

    std_values = (
        robot_audit[
            "std"
        ]
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .dropna()
    )

    positive_std = std_values[
        std_values > 0
    ]

    if len(
        positive_std
    ) > 0:

        std_ratio = (
            positive_std.max()
            / positive_std.min()
        )

    else:

        std_ratio = np.nan

    print(
        f"\n{robot}:"
    )

    print(
        f"  Smallest positive feature std: "
        f"{positive_std.min():.6f}"
        if len(positive_std)
        else
        "  No positive standard deviations."
    )

    print(
        f"  Largest feature std: "
        f"{positive_std.max():.6f}"
        if len(positive_std)
        else
        "  No positive standard deviations."
    )

    print(
        f"  Largest/smallest std ratio: "
        f"{std_ratio:.2f}"
        if pd.notna(std_ratio)
        else
        "  Standard-deviation ratio unavailable."
    )


print(
    "\nInterpretation:"
)

print(
    "PCA is variance-based. Therefore the final PCA feature matrix "
    "should be standardized before fitting PCA."
)


# =============================================================================
# 11. RAW-SAMPLE PCA CAUTION
# =============================================================================

print("\n" + "=" * 90)
print("ANALYTICAL-UNIT ASSESSMENT")
print("=" * 90)

print(
    """
The operational telemetry contains repeated samples within each
production stage.

Running PCA directly on every raw telemetry row would answer:

    "What patterns dominate individual robot telemetry samples?"

That may be technically valid, but it risks producing components that
mainly represent normal robot movement and dwell states.

The business question is concerned with cycle-time bottlenecks,
throughput and production performance.

Therefore a stronger business-aligned PCA design is to aggregate robot
motion into process-stage / cycle-level features before fitting PCA.

Examples include:

    - mean absolute joint velocity,
    - joint-velocity variability,
    - joint-position path length,
    - XY tool path length,
    - stage duration,
    - robot activity by process stage.

This allows PCA to represent multivariate operating behaviour at the
same analytical level as the production process.
"""
)


# =============================================================================
# 12. PCA SUITABILITY DECISION METRICS
# =============================================================================

total_features = (
    len(ur3_features)
    + len(ur5_features)
)

total_pairs = len(
    correlations
)

total_high_corr = int(
    correlations[
        "high_correlation"
    ].sum()
)

overall_mean_abs_corr = (
    correlations[
        "abs_correlation"
    ].mean()
)

overall_max_abs_corr = (
    correlations[
        "abs_correlation"
    ].max()
)

constant_count = int(
    audit[
        "constant_feature"
    ].sum()
)

near_constant_count = int(
    audit[
        "near_constant_feature"
    ].sum()
)


print("\n" + "=" * 90)
print("PCA SUITABILITY SUMMARY")
print("=" * 90)

print(
    f"\nTotal candidate signals across robots: "
    f"{total_features}"
)

print(
    f"Total within-robot feature pairs examined: "
    f"{total_pairs}"
)

print(
    f"Pairs with |r| >= 0.80: "
    f"{total_high_corr}"
)

print(
    f"Overall mean absolute correlation: "
    f"{overall_mean_abs_corr:.4f}"
)

print(
    f"Maximum absolute correlation: "
    f"{overall_max_abs_corr:.4f}"
)

print(
    f"Constant features: "
    f"{constant_count}"
)

print(
    f"Near-constant features: "
    f"{near_constant_count}"
)


# =============================================================================
# 13. BUILD OUTPUT TABLE
# =============================================================================

audit_output = audit.copy()

audit_output[
    "analysis_type"
] = "feature_quality"


correlation_output = correlations.copy()

correlation_output[
    "feature"
] = (
    correlation_output[
        "feature_1"
    ]
    + " vs "
    + correlation_output[
        "feature_2"
    ]
)

correlation_output[
    "analysis_type"
] = "pairwise_correlation"


# Align schemas for one audit output.
all_columns = sorted(
    set(
        audit_output.columns
    )
    | set(
        correlation_output.columns
    )
)

audit_output = audit_output.reindex(
    columns=all_columns
)

correlation_output = correlation_output.reindex(
    columns=all_columns
)

output = pd.concat(
    [
        audit_output,
        correlation_output,
    ],
    ignore_index=True,
)


output.to_csv(
    OUTPUT_FILE,
    index=False,
)


# =============================================================================
# 14. OUTPUT
# =============================================================================

print("\n" + "=" * 90)
print("OUTPUT")
print("=" * 90)

print(
    f"\nSaved:\n"
    f"{OUTPUT_FILE}"
)

print(
    f"\nOutput shape: "
    f"{output.shape}"
)


# =============================================================================
# 15. DECISION FRAME
# =============================================================================

print("\n" + "=" * 90)
print("DECISION FRAME")
print("=" * 90)

if (
    total_high_corr > 0
    or overall_mean_abs_corr >= 0.30
):

    print(
        """
The telemetry contains measurable multivariate dependence/redundancy.

PCA is therefore potentially useful as a dimensionality-reduction
method.

However, this script does NOT yet establish that PCA produces a useful
business representation.

The recommended next test is process-stage / cycle-level feature
construction followed by standardized PCA and explained-variance
analysis.
"""
    )

else:

    print(
        """
The selected telemetry signals show relatively weak pairwise
dependence.

This does not mathematically prohibit PCA, but dimensionality reduction
may provide limited analytical value.

Before proceeding, the feature design should be reconsidered rather
than applying PCA automatically.
"""
    )


print(
    """
MLflow decision:

No MLflow experiment is created at this stage.

MLflow will only be introduced if the subsequent PCA / anomaly-analysis
stage produces multiple legitimate modelling experiments that benefit
from experiment tracking.
"""
)