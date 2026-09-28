# NIST Dual-Robot Operational Analytics

## Business Question

> **How can we leverage dual-robot cell data to eliminate cycle-time bottlenecks, thereby maximizing throughput, recovering lost production hours, and reducing the manufacturing cost per part?**

## Project Overview

This project develops an end-to-end operational analytics pipeline for a dual-robot manufacturing work cell using data acquired from a National Institute of Standards and Technology (NIST) smart-manufacturing test environment.

The analysis integrates production-event data with UR3 and UR5 robot telemetry to reconstruct the production process, establish steady-state operating behaviour, identify capacity constraints, quantify throughput opportunities, and translate cycle-time improvements into benchmark-assisted economic scenarios.

The project extends my earlier UR3 operational analytics work from single-robot condition and behaviour analysis into production-level analysis of a concurrent dual-robot manufacturing system.

---

## Analytical Architecture

The project combines four complementary data layers:

- **PartData** — production events and part-level process timestamps
- **UR3 PLC telemetry** — joint position and velocity data
- **UR5 PLC telemetry** — joint position and velocity data
- **UR5 RTDE telemetry** — high-frequency physical robot telemetry

The production process was reconstructed across 60 manufactured parts and aligned with robot telemetry to analyse process stages, robot motion, cycle timing, throughput and operating behaviour.

---

## Key Results

| Metric | Result |
|---|---:|
| Parts analysed | 60 |
| Steady-state production heartbeat | 44.32 sec/part |
| Steady-state throughput | 81.23 parts/hour |
| Capacity-setting task process | 44.33 sec |
| Task action | 36.94 sec |
| Recurring transition | 7.39 sec |
| PCA variance retained | 93.00% |
| PCA components retained | 4 |
| Steady-state exploratory high-deviation rate | 2.00% |

### Capacity Constraint

The central production process exhibited a highly stable heartbeat of approximately **44.32 seconds per part**.

The t6→t9 task process averaged approximately **44.33 seconds**, making it the leading candidate for the capacity-setting process.

The recurring timing architecture consisted primarily of:

- **36.94 sec task action**
- **7.39 sec recurring transition sequence**

The evidence supports a stable, repeating production constraint rather than an intermittent slow-cycle problem.

Because the cell operates as a concurrent and pipelined dual-robot system, the analysis does **not** claim that one robot independently causes the production constraint.

---

## Dual-Robot Motion Analysis

Robot motion signatures were analysed across individual production stages.

The results strongly support the interpretation that:

- **UR5** performs the dominant material-handling activity across input and output transfer stages.
- **UR3** shows motion signatures consistent with the task/drawing process, particularly around task boundaries.

This role interpretation is empirical and based on observed motion signatures rather than treated as a directly labelled source-data field.

---

## PCA Operating-Behaviour Analysis

Standardized Principal Component Analysis was applied to 12 physical UR3 and UR5 motion features aggregated at process-stage level.

The first four principal components retained approximately **93% of total variance**.

Stage-aware PCA deviation analysis showed:

| Production Phase | Exploratory High-Deviation Rate |
|---|---:|
| Startup | 23.73% |
| Steady State | 2.00% |
| Runout | 16.67% |

The concentration of deviations during startup and runout, together with stable central production, indicates that the strongest multivariate deviations primarily represent different operating regimes.

Extreme steady-state PCA deviations showed virtually no linear relationship with the production heartbeat.

Therefore, the evidence supports an **architecture-driven capacity constraint rather than an anomaly-driven production problem**.

---

## Throughput Recovery Scenarios

Controlled cycle-time reduction scenarios were evaluated against the observed steady-state production heartbeat.

| Cycle-Time Reduction | Scenario Throughput | Throughput Gain | Time Recovered / 1,000 Parts |
|---:|---:|---:|---:|
| 0 sec | 81.23 parts/hr | 0.00% | 0.00 min |
| 1 sec | 83.11 parts/hr | 2.31% | 16.67 min |
| 2 sec | 85.07 parts/hr | 4.73% | 33.33 min |
| 3 sec | 87.13 parts/hr | 7.26% | 50.00 min |
| 4 sec | 89.29 parts/hr | 9.92% | 66.67 min |
| 5 sec | 91.56 parts/hr | 12.72% | 83.33 min |

These figures are **scenario outputs rather than observed production improvements**.

They assume that a controlled reduction in the current production heartbeat translates into equivalent cycle-time improvement without another robot, fixture, handling activity, safety requirement or process dependency becoming the new constraint.

---

## Benchmark-Assisted Cost per Part

The NIST production data does not contain complete manufacturing financial data.

Rather than inventing a manufacturing cost, the project therefore constructs a transparent **benchmark-assisted time-dependent cost model**.

### Labour Benchmark

U.S. Bureau of Labor Statistics Employer Costs for Employee Compensation data for manufacturing (June 2026):

- Wages and salaries: **$32.50/hour**
- Benefits: **$16.12/hour**
- Total employer compensation benchmark: **$48.62/hour**

Source: U.S. Bureau of Labor Statistics — Employer Costs for Employee Compensation.

### Electricity Benchmark

The U.S. Energy Information Administration reported a 2025 U.S. average industrial electricity price of:

**8.62 cents/kWh**

Source: U.S. Energy Information Administration.

### Robot Power Proxy

Published Universal Robots specifications were used as power-consumption proxies:

- UR3e typical-program power proxy: approximately **150 W**
- UR5e typical-program power proxy: approximately **200 W**

Combined robot power proxy:

**0.350 kW**

These are manufacturer specifications used as analytical proxies and are **not measured electricity consumption from the NIST experiment**.

### Economic Scenario

Under the 1.0 FTE benchmark scenario:

| Scenario | Time-Dependent Cost Component |
|---|---:|
| Baseline | ~$0.599/part |
| 5-second reduction | ~$0.531/part |
| Relative reduction | ~11.28% |

The 11.28% figure represents the modeled reduction in the **time-dependent operating-cost component per part**.

It must **not** be interpreted as an 11.28% reduction in total manufacturing cost.

The benchmark model excludes materials, tooling, maintenance, depreciation, PLC/computer electricity, facility overhead, HVAC, compressed air, quality costs, financing, downtime and other manufacturing costs not contained in the source dataset.

---

## Operational Interpretation

The analysis indicates that the production system is characterized by:

- A highly stable steady-state production heartbeat
- A recurring capacity-setting task process
- Deterministic two-fixture timing behaviour
- Concurrent UR3 and UR5 operation
- Stable steady-state multivariate robot behaviour
- Stronger PCA deviations during startup and runout
- Little evidence that extreme steady-state robot deviations explain production cadence

The strongest improvement opportunities therefore lie in examining:

**task execution time, recurring transitions, robot synchronization, handoffs and safe process overlap.**

---

## Technology Stack

**Python | Pandas | NumPy | Scikit-learn | PCA | Time-Series Analytics | Industrial Robotics | PLC/RTDE Data | Process Analytics | Throughput Modelling | Tableau | Git**

---

## Analytical Pipeline

The repository preserves the complete analytical workflow as numbered Python scripts:

```text
01_data_inventory.py
02_partdata_schema_audit.py
03_partdata_normalization.py
04_cycle_stage_analysis.py
05_dual_robot_timeline_alignment.py
06_dual_robot_operational_analysis.py
07_telemetry_process_coverage.py
08_time_scale_resolution.py
09_full_process_robot_alignment.py
10_resource_contention_analysis.py
11_steady_state_throughput_analysis.py
12_bottleneck_cycle_decomposition.py
13_robot_role_identification.py
14_robot_motion_signature_analysis.py
15_bottleneck_validation.py
16_throughput_recovery_scenarios.py
17_benchmark_cost_per_part_analysis.py
18_final_analytical_dataset.py
19_pca_suitability_analysis.py
20_pca_feature_matrix.py
21_standardized_pca_analysis.py
22_pca_operating_behaviour_analysis.py
23_steady_state_operating_baseline_validation.py
24_final_analytical_consolidation.py