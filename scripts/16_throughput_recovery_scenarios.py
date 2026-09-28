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
    / "bottleneck_validation.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "throughput_recovery_scenarios.csv"
)


# =============================================================================
# 2. LOAD VALIDATED BOTTLENECK DATA
# =============================================================================

df = pd.read_csv(INPUT_FILE)

print("=" * 80)
print("NIST ROBOTIC WORK CELL - THROUGHPUT RECOVERY SCENARIOS")
print("=" * 80)

print(f"\nValidation rows: {len(df):,}")


# =============================================================================
# 3. ESTABLISH OBSERVED BASELINE
# =============================================================================

baseline_output_cycle_sec = (
    df["part_removed_heartbeat_sec"]
    .dropna()
    .mean()
)

baseline_task_cycle_sec = (
    df["task_process_sec"]
    .dropna()
    .mean()
)

baseline_task_start_cycle_sec = (
    df["task_start_heartbeat_sec"]
    .dropna()
    .mean()
)

baseline_parts_per_hour = (
    3600
    / baseline_output_cycle_sec
)


print("\n" + "=" * 80)
print("OBSERVED STEADY-STATE BASELINE")
print("=" * 80)

print(
    f"\nMean t6->t9 task process: "
    f"{baseline_task_cycle_sec:.4f} sec"
)

print(
    f"Mean TaskStart heartbeat: "
    f"{baseline_task_start_cycle_sec:.4f} sec"
)

print(
    f"Mean PartRemoved heartbeat: "
    f"{baseline_output_cycle_sec:.4f} sec"
)

print(
    f"Observed throughput: "
    f"{baseline_parts_per_hour:.2f} parts/hour"
)


# =============================================================================
# 4. SCENARIO ASSUMPTIONS
# =============================================================================

# These are hypothetical controlled reductions in the capacity-setting
# production cycle.
#
# They are NOT observed improvements and are NOT predictions.
#
# The scenario assumes that a reduction in the capacity-setting task cycle
# can translate one-for-one into a reduction in the steady-state production
# heartbeat, with no new downstream or upstream constraint becoming active.

REDUCTION_SCENARIOS_SEC = [
    0,
    1,
    2,
    3,
    4,
    5,
]

PRODUCTION_QUANTITIES = [
    100,
    500,
    1000,
    5000,
]

OPERATING_HOURS = [
    8,
    12,
    24,
]


# =============================================================================
# 5. BUILD THROUGHPUT SCENARIOS
# =============================================================================

scenario_rows = []

for reduction_sec in REDUCTION_SCENARIOS_SEC:

    scenario_cycle_sec = (
        baseline_output_cycle_sec
        - reduction_sec
    )

    if scenario_cycle_sec <= 0:
        continue

    scenario_pph = (
        3600
        / scenario_cycle_sec
    )

    additional_pph = (
        scenario_pph
        - baseline_parts_per_hour
    )

    throughput_gain_pct = (
        additional_pph
        / baseline_parts_per_hour
        * 100
    )

    scenario_rows.append({
        "cycle_reduction_sec":
            reduction_sec,

        "baseline_cycle_sec":
            baseline_output_cycle_sec,

        "scenario_cycle_sec":
            scenario_cycle_sec,

        "baseline_parts_per_hour":
            baseline_parts_per_hour,

        "scenario_parts_per_hour":
            scenario_pph,

        "additional_parts_per_hour":
            additional_pph,

        "throughput_gain_pct":
            throughput_gain_pct,
    })


scenarios = pd.DataFrame(
    scenario_rows
)


# =============================================================================
# 6. CORE THROUGHPUT IMPACT
# =============================================================================

print("\n" + "=" * 80)
print("THROUGHPUT IMPACT BY CYCLE-TIME REDUCTION")
print("=" * 80)

print(
    scenarios
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 7. CAPACITY GAIN BY OPERATING PERIOD
# =============================================================================

print("\n" + "=" * 80)
print("ADDITIONAL CAPACITY BY OPERATING PERIOD")
print("=" * 80)

capacity_rows = []

for _, scenario in scenarios.iterrows():

    for hours in OPERATING_HOURS:

        baseline_capacity = (
            scenario[
                "baseline_parts_per_hour"
            ]
            * hours
        )

        scenario_capacity = (
            scenario[
                "scenario_parts_per_hour"
            ]
            * hours
        )

        additional_capacity = (
            scenario_capacity
            - baseline_capacity
        )

        capacity_rows.append({
            "cycle_reduction_sec":
                scenario[
                    "cycle_reduction_sec"
                ],

            "operating_hours":
                hours,

            "baseline_parts":
                baseline_capacity,

            "scenario_parts":
                scenario_capacity,

            "additional_parts":
                additional_capacity,
        })


capacity = pd.DataFrame(
    capacity_rows
)

print(
    capacity
    .round(2)
    .to_string(index=False)
)


# =============================================================================
# 8. PRODUCTION TIME RECOVERY
# =============================================================================

print("\n" + "=" * 80)
print("PRODUCTION TIME RECOVERY FOR FIXED OUTPUT")
print("=" * 80)

time_rows = []

for _, scenario in scenarios.iterrows():

    for quantity in PRODUCTION_QUANTITIES:

        baseline_hours = (
            quantity
            / scenario[
                "baseline_parts_per_hour"
            ]
        )

        scenario_hours = (
            quantity
            / scenario[
                "scenario_parts_per_hour"
            ]
        )

        hours_saved = (
            baseline_hours
            - scenario_hours
        )

        minutes_saved = (
            hours_saved
            * 60
        )

        time_rows.append({
            "cycle_reduction_sec":
                scenario[
                    "cycle_reduction_sec"
                ],

            "production_quantity":
                quantity,

            "baseline_hours":
                baseline_hours,

            "scenario_hours":
                scenario_hours,

            "hours_saved":
                hours_saved,

            "minutes_saved":
                minutes_saved,
        })


time_recovery = pd.DataFrame(
    time_rows
)

print(
    time_recovery
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 9. FOCUS: 1,000-PART PRODUCTION RUN
# =============================================================================

print("\n" + "=" * 80)
print("1,000-PART PRODUCTION RUN")
print("=" * 80)

quantity = 1000

focus_rows = []

for _, scenario in scenarios.iterrows():

    baseline_hours = (
        quantity
        / scenario[
            "baseline_parts_per_hour"
        ]
    )

    scenario_hours = (
        quantity
        / scenario[
            "scenario_parts_per_hour"
        ]
    )

    hours_saved = (
        baseline_hours
        - scenario_hours
    )

    focus_rows.append({
        "cycle_reduction_sec":
            scenario[
                "cycle_reduction_sec"
            ],

        "scenario_cycle_sec":
            scenario[
                "scenario_cycle_sec"
            ],

        "parts_per_hour":
            scenario[
                "scenario_parts_per_hour"
            ],

        "throughput_gain_pct":
            scenario[
                "throughput_gain_pct"
            ],

        "hours_for_1000_parts":
            scenario_hours,

        "hours_saved_per_1000_parts":
            hours_saved,

        "minutes_saved_per_1000_parts":
            hours_saved * 60,
    })


focus = pd.DataFrame(
    focus_rows
)

print(
    focus
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 10. FOCUS: 8 / 12 / 24-HOUR CAPACITY
# =============================================================================

print("\n" + "=" * 80)
print("SHIFT CAPACITY SUMMARY")
print("=" * 80)

shift_rows = []

for _, scenario in scenarios.iterrows():

    row = {
        "cycle_reduction_sec":
            scenario[
                "cycle_reduction_sec"
            ],

        "scenario_cycle_sec":
            scenario[
                "scenario_cycle_sec"
            ],

        "parts_per_hour":
            scenario[
                "scenario_parts_per_hour"
            ],
    }

    for hours in OPERATING_HOURS:

        scenario_parts = (
            scenario[
                "scenario_parts_per_hour"
            ]
            * hours
        )

        baseline_parts = (
            baseline_parts_per_hour
            * hours
        )

        row[
            f"parts_{hours}h"
        ] = scenario_parts

        row[
            f"additional_parts_{hours}h"
        ] = (
            scenario_parts
            - baseline_parts
        )

    shift_rows.append(row)


shift_summary = pd.DataFrame(
    shift_rows
)

print(
    shift_summary
    .round(2)
    .to_string(index=False)
)


# =============================================================================
# 11. RELATIVE CAPACITY INDEX
# =============================================================================

print("\n" + "=" * 80)
print("RELATIVE CAPACITY INDEX")
print("=" * 80)

capacity_index = scenarios[
    [
        "cycle_reduction_sec",
        "scenario_cycle_sec",
        "scenario_parts_per_hour",
        "throughput_gain_pct",
    ]
].copy()

capacity_index[
    "capacity_index_baseline_100"
] = (
    capacity_index[
        "scenario_parts_per_hour"
    ]
    / baseline_parts_per_hour
    * 100
)

print(
    capacity_index
    .round(4)
    .to_string(index=False)
)


# =============================================================================
# 12. SIMPLE SCENARIO CHECK
# =============================================================================

print("\n" + "=" * 80)
print("SCENARIO INTERPRETATION CHECK")
print("=" * 80)

for _, row in scenarios.iterrows():

    reduction = (
        row["cycle_reduction_sec"]
    )

    if reduction == 0:
        continue

    print(
        f"\n{reduction:.0f}-second reduction:"
    )

    print(
        f"  New cycle: "
        f"{row['scenario_cycle_sec']:.4f} sec"
    )

    print(
        f"  Throughput: "
        f"{row['scenario_parts_per_hour']:.2f} parts/hour"
    )

    print(
        f"  Gain: "
        f"{row['additional_parts_per_hour']:.2f} parts/hour"
    )

    print(
        f"  Relative improvement: "
        f"{row['throughput_gain_pct']:.2f}%"
    )


# =============================================================================
# 13. SAVE CONSOLIDATED SCENARIO TABLE
# =============================================================================

# Add useful shift and fixed-volume fields to one final analytical table.

final = scenarios.copy()

for hours in OPERATING_HOURS:

    final[
        f"baseline_parts_{hours}h"
    ] = (
        baseline_parts_per_hour
        * hours
    )

    final[
        f"scenario_parts_{hours}h"
    ] = (
        final[
            "scenario_parts_per_hour"
        ]
        * hours
    )

    final[
        f"additional_parts_{hours}h"
    ] = (
        final[
            f"scenario_parts_{hours}h"
        ]
        - final[
            f"baseline_parts_{hours}h"
        ]
    )


for quantity in PRODUCTION_QUANTITIES:

    baseline_hours = (
        quantity
        / baseline_parts_per_hour
    )

    final[
        f"hours_for_{quantity}_parts"
    ] = (
        quantity
        / final[
            "scenario_parts_per_hour"
        ]
    )

    final[
        f"hours_saved_{quantity}_parts"
    ] = (
        baseline_hours
        - final[
            f"hours_for_{quantity}_parts"
        ]
    )


OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

final.to_csv(
    OUTPUT_FILE,
    index=False,
)


# =============================================================================
# 14. OUTPUT
# =============================================================================

print("\n" + "=" * 80)
print("OUTPUT")
print("=" * 80)

print(
    f"\nSaved:\n{OUTPUT_FILE}"
)

print(
    f"\nOutput shape: "
    f"{final.shape}"
)


# =============================================================================
# 15. ANALYTICAL NOTE
# =============================================================================

print("\n" + "=" * 80)
print("ANALYTICAL NOTE")
print("=" * 80)

print(
    """
These are scenario calculations, not observed production improvements
and not predictive model outputs.

The observed steady-state PartRemoved heartbeat is used as the baseline
production cycle.

Each scenario assumes that a controlled reduction in the capacity-setting
cycle translates one-for-one into a reduction in the production heartbeat.

That assumption requires the current task process to remain the active
throughput constraint. If another robot, fixture, material-handling step,
safety condition or process dependency becomes limiting after improvement,
the realized throughput gain would be lower than the scenario calculation.

Therefore these results represent transparent operational opportunity
scenarios under an explicit constraint-preservation assumption.

No monetary savings or cost-per-part reductions are calculated because
the source data does not contain the required financial inputs.
"""
)