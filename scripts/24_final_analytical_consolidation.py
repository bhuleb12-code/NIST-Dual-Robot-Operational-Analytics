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

PROCESSED = (
    PROJECT_ROOT
    / "data"
    / "processed"
)


# Existing analytical outputs
KPI_FILE = (
    PROCESSED
    / "final_operational_kpis.csv"
)

SCENARIO_FILE = (
    PROCESSED
    / "final_throughput_cost_scenarios.csv"
)

EVIDENCE_FILE = (
    PROCESSED
    / "final_evidence_register.csv"
)

PCA_VARIANCE_FILE = (
    PROCESSED
    / "pca_explained_variance.csv"
)

PCA_DEVIATION_FILE = (
    PROCESSED
    / "pca_within_stage_deviation.csv"
)

STEADY_STATE_FILE = (
    PROCESSED
    / "steady_state_cycle_behaviour_validation.csv"
)


# New consolidated outputs
FINAL_KPI_FILE = (
    PROCESSED
    / "final_project_kpis.csv"
)

FINAL_SCENARIO_FILE = (
    PROCESSED
    / "final_project_scenarios.csv"
)

FINAL_EVIDENCE_FILE = (
    PROCESSED
    / "final_project_evidence_register.csv"
)

FINAL_PCA_SUMMARY_FILE = (
    PROCESSED
    / "final_operating_behaviour_summary.csv"
)


# =============================================================================
# 2. PROJECT BUSINESS QUESTION
# =============================================================================

BUSINESS_QUESTION = (
    "How can we leverage dual-robot cell data to eliminate cycle-time "
    "bottlenecks, thereby maximizing throughput, recovering lost production "
    "hours, and reducing the manufacturing cost per part?"
)


# =============================================================================
# 3. LOAD INPUTS
# =============================================================================

print("=" * 95)
print("NIST ROBOTIC WORK CELL - FINAL ANALYTICAL CONSOLIDATION")
print("=" * 95)


required_files = [
    KPI_FILE,
    SCENARIO_FILE,
    EVIDENCE_FILE,
    PCA_VARIANCE_FILE,
    PCA_DEVIATION_FILE,
    STEADY_STATE_FILE,
]


for file in required_files:

    if not file.exists():

        raise FileNotFoundError(
            f"Required analytical output not found:\n{file}"
        )


kpis = pd.read_csv(KPI_FILE)
scenarios = pd.read_csv(SCENARIO_FILE)
evidence = pd.read_csv(EVIDENCE_FILE)
pca_variance = pd.read_csv(PCA_VARIANCE_FILE)
pca_deviation = pd.read_csv(PCA_DEVIATION_FILE)
steady_state = pd.read_csv(STEADY_STATE_FILE)


print("\nLoaded analytical outputs:")

print(
    f"Operational KPIs:             "
    f"{kpis.shape}"
)

print(
    f"Throughput/cost scenarios:    "
    f"{scenarios.shape}"
)

print(
    f"Evidence register:            "
    f"{evidence.shape}"
)

print(
    f"PCA explained variance:       "
    f"{pca_variance.shape}"
)

print(
    f"PCA deviation observations:   "
    f"{pca_deviation.shape}"
)

print(
    f"Steady-state cycle behaviour: "
    f"{steady_state.shape}"
)


# =============================================================================
# 4. BUSINESS QUESTION
# =============================================================================

print("\n" + "=" * 95)
print("BUSINESS QUESTION")
print("=" * 95)

print(
    f"\n{BUSINESS_QUESTION}"
)


# =============================================================================
# 5. PCA COMPRESSION RESULTS
# =============================================================================

print("\n" + "=" * 95)
print("MULTIVARIATE OPERATING-BEHAVIOUR REPRESENTATION")
print("=" * 95)


pca_variance[
    "component"
] = (
    pca_variance[
        "component"
    ]
    .astype(str)
)


pc4_row = (
    pca_variance[
        pca_variance["component"] == "PC4"
    ]
)


if len(pc4_row) != 1:

    raise ValueError(
        "Could not uniquely identify PC4 "
        "in PCA explained-variance output."
    )


pc4_cumulative_pct = float(
    pc4_row[
        "cumulative_variance_pct"
    ]
    .iloc[0]
)


pc2_row = (
    pca_variance[
        pca_variance["component"] == "PC2"
    ]
)


pc2_cumulative_pct = float(
    pc2_row[
        "cumulative_variance_pct"
    ]
    .iloc[0]
)


print(
    f"\nOriginal physical motion features: 12"
)

print(
    f"PC1-PC2 cumulative variance: "
    f"{pc2_cumulative_pct:.2f}%"
)

print(
    f"PC1-PC4 cumulative variance: "
    f"{pc4_cumulative_pct:.2f}%"
)


# =============================================================================
# 6. PRODUCTION-REGION PCA BEHAVIOUR
# =============================================================================

pca_deviation[
    "cycle_id"
] = pd.to_numeric(
    pca_deviation["cycle_id"],
    errors="coerce",
)


def production_region(cycle_id):

    if pd.isna(cycle_id):
        return np.nan

    if cycle_id <= 5:
        return "Startup"

    if cycle_id >= 56:
        return "Runout"

    return "Steady State"


pca_deviation[
    "production_region"
] = (
    pca_deviation[
        "cycle_id"
    ]
    .apply(
        production_region
    )
)


if (
    pca_deviation[
        "stage_high_deviation"
    ]
    .dtype
    != bool
):

    pca_deviation[
        "stage_high_deviation"
    ] = (
        pca_deviation[
            "stage_high_deviation"
        ]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
            }
        )
    )


region_summary = (
    pca_deviation
    .groupby(
        "production_region",
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

        high_deviation_observations=(
            "stage_high_deviation",
            "sum",
        ),
    )
)


region_summary[
    "high_deviation_pct"
] = (
    region_summary[
        "high_deviation_observations"
    ]
    /
    region_summary[
        "observations"
    ]
    * 100
)


region_order = {
    "Startup": 1,
    "Steady State": 2,
    "Runout": 3,
}


region_summary[
    "_order"
] = (
    region_summary[
        "production_region"
    ]
    .map(
        region_order
    )
)


region_summary = (
    region_summary
    .sort_values(
        "_order"
    )
    .drop(
        columns="_order"
    )
)


print("\n" + "=" * 95)
print("OPERATING-BEHAVIOUR DEVIATION BY PRODUCTION REGION")
print("=" * 95)


print(
    region_summary
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 7. STEADY-STATE PCA / HEARTBEAT VALIDATION
# =============================================================================

print("\n" + "=" * 95)
print("STEADY-STATE OPERATING-BEHAVIOUR VALIDATION")
print("=" * 95)


steady_metrics = [
    "mean_pca_distance",
    "max_pca_distance",
    "high_deviation_stages",
    "task_start_heartbeat_sec",
    "part_removed_heartbeat_sec",
]


missing_steady = [
    col
    for col in steady_metrics
    if col not in steady_state.columns
]


if missing_steady:

    raise ValueError(
        f"Missing steady-state columns:\n"
        f"{missing_steady}"
    )


mean_distance_task_corr = (
    steady_state[
        "mean_pca_distance"
    ]
    .corr(
        steady_state[
            "task_start_heartbeat_sec"
        ]
    )
)


mean_distance_output_corr = (
    steady_state[
        "mean_pca_distance"
    ]
    .corr(
        steady_state[
            "part_removed_heartbeat_sec"
        ]
    )
)


max_distance_task_corr = (
    steady_state[
        "max_pca_distance"
    ]
    .corr(
        steady_state[
            "task_start_heartbeat_sec"
        ]
    )
)


max_distance_output_corr = (
    steady_state[
        "max_pca_distance"
    ]
    .corr(
        steady_state[
            "part_removed_heartbeat_sec"
        ]
    )
)


task_heartbeat_mean = (
    steady_state[
        "task_start_heartbeat_sec"
    ]
    .mean()
)


task_heartbeat_std = (
    steady_state[
        "task_start_heartbeat_sec"
    ]
    .std()
)


output_heartbeat_mean = (
    steady_state[
        "part_removed_heartbeat_sec"
    ]
    .mean()
)


output_heartbeat_std = (
    steady_state[
        "part_removed_heartbeat_sec"
    ]
    .std()
)


print(
    f"\nTaskStart heartbeat: "
    f"{task_heartbeat_mean:.4f} sec "
    f"(SD {task_heartbeat_std:.4f})"
)

print(
    f"PartRemoved heartbeat: "
    f"{output_heartbeat_mean:.4f} sec "
    f"(SD {output_heartbeat_std:.4f})"
)


print(
    f"\nMean PCA distance vs TaskStart heartbeat: "
    f"{mean_distance_task_corr:.4f}"
)

print(
    f"Mean PCA distance vs PartRemoved heartbeat: "
    f"{mean_distance_output_corr:.4f}"
)

print(
    f"Max PCA distance vs TaskStart heartbeat: "
    f"{max_distance_task_corr:.4f}"
)

print(
    f"Max PCA distance vs PartRemoved heartbeat: "
    f"{max_distance_output_corr:.4f}"
)


# =============================================================================
# 8. CREATE FINAL OPERATING-BEHAVIOUR SUMMARY
# =============================================================================

operating_summary_rows = []


def add_operating_metric(
    metric,
    value,
    unit,
    interpretation,
    evidence_type,
):

    operating_summary_rows.append(
        {
            "metric":
                metric,

            "value":
                value,

            "unit":
                unit,

            "interpretation":
                interpretation,

            "evidence_type":
                evidence_type,
        }
    )


add_operating_metric(
    "PCA input physical motion features",
    12,
    "features",
    (
        "Underlying UR3 and UR5 process-stage "
        "motion features entered standardized PCA."
    ),
    "Project-derived",
)


add_operating_metric(
    "PCA retained components",
    4,
    "components",
    (
        "Four components retained as the "
        "operating-behaviour representation."
    ),
    "Project-derived",
)


add_operating_metric(
    "Variance retained by PC1-PC4",
    pc4_cumulative_pct,
    "percent",
    (
        "Four principal components preserve "
        "approximately 93% of standardized "
        "dual-robot motion variance."
    ),
    "Project-derived",
)


for _, row in region_summary.iterrows():

    add_operating_metric(
        (
            f"{row['production_region']} "
            f"high-deviation rate"
        ),
        row[
            "high_deviation_pct"
        ],
        "percent",
        (
            "Exploratory stage-aware PCA "
            "high-deviation rate."
        ),
        "Project-derived exploratory",
    )


add_operating_metric(
    "Steady-state TaskStart heartbeat",
    task_heartbeat_mean,
    "seconds per part",
    (
        "Observed central production cadence."
    ),
    "Observed/project-derived",
)


add_operating_metric(
    "Steady-state PartRemoved heartbeat",
    output_heartbeat_mean,
    "seconds per part",
    (
        "Observed output production cadence."
    ),
    "Observed/project-derived",
)


add_operating_metric(
    "Max PCA distance vs TaskStart heartbeat correlation",
    max_distance_task_corr,
    "correlation",
    (
        "Extreme within-cycle multivariate "
        "deviation showed virtually no linear "
        "relationship with TaskStart cadence."
    ),
    "Project-derived descriptive",
)


add_operating_metric(
    "Max PCA distance vs PartRemoved heartbeat correlation",
    max_distance_output_corr,
    "correlation",
    (
        "Extreme within-cycle multivariate "
        "deviation showed virtually no linear "
        "relationship with output cadence."
    ),
    "Project-derived descriptive",
)


operating_summary = pd.DataFrame(
    operating_summary_rows
)


print("\n" + "=" * 95)
print("FINAL OPERATING-BEHAVIOUR SUMMARY")
print("=" * 95)


print(
    operating_summary
    .round(4)
    .to_string(
        index=False
    )
)


# =============================================================================
# 9. EXTEND KPI LAYER
# =============================================================================

final_kpis = kpis.copy()


new_kpi_rows = []


# Match existing KPI file columns without assuming their exact schema.
print("\n" + "=" * 95)
print("EXISTING KPI SCHEMA")
print("=" * 95)

print(
    list(
        final_kpis.columns
    )
)


# =============================================================================
# 10. CREATE DASHBOARD-SAFE KPI TABLE
# =============================================================================

# Rather than altering the original Script 18 schema blindly,
# build a clean, stable business-facing KPI table.

dashboard_kpis = pd.DataFrame(
    [
        {
            "kpi":
                "Parts Observed",
            "value":
                60,
            "unit":
                "parts",
            "category":
                "Production",
            "evidence_type":
                "Observed",
        },

        {
            "kpi":
                "Steady-State Heartbeat",
            "value":
                output_heartbeat_mean,
            "unit":
                "sec/part",
            "category":
                "Production",
            "evidence_type":
                "Project-derived",
        },

        {
            "kpi":
                "Steady-State Throughput",
            "value":
                3600
                / output_heartbeat_mean,
            "unit":
                "parts/hour",
            "category":
                "Production",
            "evidence_type":
                "Project-derived",
        },

        {
            "kpi":
                "Capacity-Setting Task Process",
            "value":
                44.3264,
            "unit":
                "seconds",
            "category":
                "Bottleneck",
            "evidence_type":
                "Project-derived",
        },

        {
            "kpi":
                "Task Action",
            "value":
                36.9369,
            "unit":
                "seconds",
            "category":
                "Bottleneck",
            "evidence_type":
                "Project-derived",
        },

        {
            "kpi":
                "Recurring Transition",
            "value":
                7.3869,
            "unit":
                "seconds",
            "category":
                "Bottleneck",
            "evidence_type":
                "Project-derived",
        },

        {
            "kpi":
                "PCA Variance Retained",
            "value":
                pc4_cumulative_pct,
            "unit":
                "percent",
            "category":
                "Operating Behaviour",
            "evidence_type":
                "Project-derived",
        },

        {
            "kpi":
                "Steady-State High-Deviation Rate",
            "value":
                float(
                    region_summary.loc[
                        region_summary[
                            "production_region"
                        ]
                        == "Steady State",
                        "high_deviation_pct",
                    ]
                    .iloc[0]
                ),
            "unit":
                "percent",
            "category":
                "Operating Behaviour",
            "evidence_type":
                "Exploratory",
        },
    ]
)


# =============================================================================
# 11. PRESERVE SCENARIO LAYER
# =============================================================================

final_scenarios = (
    scenarios.copy()
)


# =============================================================================
# 12. EXTEND EVIDENCE REGISTER
# =============================================================================

final_evidence = (
    evidence.copy()
)


print("\n" + "=" * 95)
print("EXISTING EVIDENCE REGISTER SCHEMA")
print("=" * 95)

print(
    list(
        final_evidence.columns
    )
)


# Build a separate normalized PCA evidence block first.
pca_evidence = pd.DataFrame(
    [
        {
            "finding":
                (
                    "Twelve standardized dual-robot motion "
                    "features were reduced to four principal "
                    "components retaining approximately "
                    f"{pc4_cumulative_pct:.2f}% of variance."
                ),
            "evidence_class":
                "Project-derived",
            "interpretation":
                (
                    "Dual-robot process-stage motion contains "
                    "substantial compressible multivariate structure."
                ),
            "limitation":
                (
                    "Principal components are mathematical "
                    "representations and are not automatically "
                    "physical machine states."
                ),
        },

        {
            "finding":
                (
                    "Stage-aware PCA deviations were concentrated "
                    "during startup and runout relative to "
                    "steady-state production."
                ),
            "evidence_class":
                "Project-derived exploratory",
            "interpretation":
                (
                    "Operating regime is important when interpreting "
                    "multivariate robot behaviour."
                ),
            "limitation":
                (
                    "95th-percentile deviation flags are exploratory "
                    "ranking devices, not failure labels."
                ),
        },

        {
            "finding":
                (
                    "Only 2.0% of stage observations in cycles "
                    "6-55 met the stage-specific exploratory "
                    "high-deviation rule."
                ),
            "evidence_class":
                "Project-derived exploratory",
            "interpretation":
                (
                    "Central steady-state robot behaviour was "
                    "comparatively stable."
                ),
            "limitation":
                (
                    "The threshold was deliberately defined from "
                    "the observed stage-specific distributions."
                ),
        },

        {
            "finding":
                (
                    "Maximum within-cycle PCA deviation had "
                    "near-zero correlation with steady-state "
                    "TaskStart and PartRemoved heartbeat."
                ),
            "evidence_class":
                "Project-derived descriptive",
            "interpretation":
                (
                    "Extreme multivariate motion deviations did not "
                    "explain the observed steady-state production cadence."
                ),
            "limitation":
                (
                    "Correlation does not establish causality, and "
                    "the dataset contains no labelled failure outcome."
                ),
        },

        {
            "finding":
                (
                    "The overall evidence supports a stable repeating "
                    "capacity-setting process architecture rather than "
                    "an intermittent anomaly-driven throughput constraint."
                ),
            "evidence_class":
                "Analytical synthesis",
            "interpretation":
                (
                    "Improvement attention should focus on recurring "
                    "task execution, transitions, synchronization and "
                    "potential safe overlap opportunities."
                ),
            "limitation":
                (
                    "The analysis does not prove that a single robot "
                    "independently causes the bottleneck because the "
                    "dual-robot cell operates concurrently."
                ),
        },
    ]
)


# =============================================================================
# 13. SAVE FINAL BUSINESS-FACING OUTPUTS
# =============================================================================

FINAL_KPI_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)


dashboard_kpis.to_csv(
    FINAL_KPI_FILE,
    index=False,
)


final_scenarios.to_csv(
    FINAL_SCENARIO_FILE,
    index=False,
)


operating_summary.to_csv(
    FINAL_PCA_SUMMARY_FILE,
    index=False,
)


# Preserve the original evidence register separately from the normalized
# PCA extension because Script 18 may use a different column structure.
#
# If schemas happen to match, append directly.
# Otherwise, save a normalized combined textual register.


normalized_original_evidence = pd.DataFrame(
    {
        "finding":
            final_evidence
            .astype(str)
            .agg(
                " | ".join,
                axis=1,
            ),

        "evidence_class":
            "Existing Script 18 evidence",

        "interpretation":
            (
                "Preserved from the pre-PCA final "
                "analytical evidence register."
            ),

        "limitation":
            (
                "Refer to original Script 18 evidence fields "
                "for detailed classification."
            ),
    }
)


combined_evidence = pd.concat(
    [
        normalized_original_evidence,
        pca_evidence,
    ],
    ignore_index=True,
)


combined_evidence.to_csv(
    FINAL_EVIDENCE_FILE,
    index=False,
)


# =============================================================================
# 14. FINAL BUSINESS RESULTS
# =============================================================================

baseline_throughput = (
    3600
    / output_heartbeat_mean
)


print("\n" + "=" * 95)
print("FINAL BUSINESS RESULTS")
print("=" * 95)


print(
    f"\nObserved parts: "
    f"60"
)

print(
    f"Steady-state heartbeat: "
    f"{output_heartbeat_mean:.4f} sec/part"
)

print(
    f"Steady-state throughput: "
    f"{baseline_throughput:.2f} parts/hour"
)

print(
    f"Capacity-setting task process: "
    f"44.3264 sec"
)

print(
    f"Task action component: "
    f"36.9369 sec"
)

print(
    f"Recurring transition component: "
    f"7.3869 sec"
)

print(
    f"PCA representation: "
    f"4 components / "
    f"{pc4_cumulative_pct:.2f}% variance"
)


steady_deviation_rate = float(
    region_summary.loc[
        region_summary[
            "production_region"
        ]
        == "Steady State",
        "high_deviation_pct",
    ]
    .iloc[0]
)


print(
    f"Steady-state exploratory "
    f"high-deviation rate: "
    f"{steady_deviation_rate:.2f}%"
)


# =============================================================================
# 15. FINAL INTERPRETATION
# =============================================================================

print("\n" + "=" * 95)
print("FINAL ANALYTICAL INTERPRETATION")
print("=" * 95)


print(
    """
The dual-robot work cell operated with a highly stable central production
heartbeat of approximately 44.32 seconds per part, equivalent to approximately
81.23 parts per hour.

The t6_t9 task process consumed approximately 44.33 seconds and remained
tightly synchronized with the observed production heartbeat. The process
consisted principally of approximately 36.94 seconds of task action and a
recurring transition sequence of approximately 7.39 seconds.

This makes the task process the leading capacity-setting process identified
by the analysis. The evidence does not establish that one robot independently
causes the bottleneck because the cell operates as a concurrent dual-robot
system.

Multivariate operating-behaviour analysis reduced twelve standardized robot
motion features to four principal components while retaining approximately
93% of their variance.

Stage-aware PCA analysis showed that the strongest multivariate deviations
were concentrated during startup and runout operating conditions. Central
steady-state production was substantially more stable.

Within steady-state production, extreme PCA deviation showed virtually no
linear relationship with the TaskStart or PartRemoved production heartbeat.
The evidence therefore does not support intermittent anomalous robot behaviour
as the primary explanation for the observed throughput constraint.

Taken together, the evidence supports a stable, repeating, architecture-driven
capacity constraint rather than an anomaly-driven production problem.

Operational improvement should therefore focus first on the recurring
capacity-setting task sequence: task execution time, transition time,
synchronization, hand-offs and any safely achievable overlap between
activities.

Throughput-recovery figures remain scenarios rather than observed improvements.
Economic results remain benchmark-assisted because actual NIST labour,
electricity, overhead and manufacturing accounting costs were not supplied.

The project therefore answers the business question through a combination of:

    1. production-flow reconstruction,
    2. dual-robot motion analysis,
    3. bottleneck decomposition,
    4. steady-state throughput measurement,
    5. throughput-recovery scenarios,
    6. benchmark-assisted cost-per-part analysis,
    7. PCA-based multivariate operating-behaviour validation.

No additional anomaly model is required by the current evidence.
"""
)


# =============================================================================
# 16. OUTPUTS
# =============================================================================

print("\n" + "=" * 95)
print("FINAL OUTPUTS")
print("=" * 95)


print(
    f"\nDashboard KPI dataset:\n"
    f"{FINAL_KPI_FILE}"
)

print(
    f"\nScenario dataset:\n"
    f"{FINAL_SCENARIO_FILE}"
)

print(
    f"\nOperating-behaviour summary:\n"
    f"{FINAL_PCA_SUMMARY_FILE}"
)

print(
    f"\nEvidence register:\n"
    f"{FINAL_EVIDENCE_FILE}"
)


print(
    f"\nKPI shape: "
    f"{dashboard_kpis.shape}"
)

print(
    f"Scenario shape: "
    f"{final_scenarios.shape}"
)

print(
    f"Operating summary shape: "
    f"{operating_summary.shape}"
)

print(
    f"Evidence register shape: "
    f"{combined_evidence.shape}"
)


print("\n" + "=" * 95)
print("ANALYTICAL PIPELINE COMPLETE")
print("=" * 95)

print(
    "\nCore production analysis: COMPLETE"
)

print(
    "Dual-robot analysis: COMPLETE"
)

print(
    "Bottleneck analysis: COMPLETE"
)

print(
    "Throughput analysis: COMPLETE"
)

print(
    "Cost-per-part scenario analysis: COMPLETE"
)

print(
    "PCA operating-behaviour analysis: COMPLETE"
)

print(
    "Final analytical consolidation: COMPLETE"
)