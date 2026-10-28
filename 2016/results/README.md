# Result Catalogue

All `.xlsx` artifacts are kept in this directory. Solution text files remain
under sibling `2016/solutions_{solver}/` trees because those are the paths used
by the batch runner.

| Method | Solver ID | Code entry point | Workbook | Solution tree |
| --- | --- | --- | --- | --- |
| Direct SAT | `directSAT` | `Encoding/directSAT.py` | `2016/results/results_directSAT.xlsx` | `2016/solutions_directSAT/` |
| Proposed SAT | `proposedSAT` | `Encoding/proposedSAT.py` | `2016/results/results_proposedSAT.xlsx` | `2016/solutions_proposedSAT/` |
| MIP | `cplex_mp` | `Encoding/cplex_mp.py` | `2016/results/results_cplex_mp.xlsx` | `2016/solutions_cplex_mp/` |
| MIP | `gurobi` | `Encoding/gurobi.py` | `2016/results/results_gurobi.xlsx` | `2016/solutions_gurobi/` |
| CP | `cplex_cp` | `Encoding/cplex_cp.py` | `2016/results/results_cplex_cp.xlsx` | `2016/solutions_cplex_cp/` |
| CP | `cpsat` | `Encoding/cpsat.py` | `2016/results/results_cpsat.xlsx` | `2016/solutions_cpsat/` |

The workbook sheets follow the dataset names `10-S`, `10-L`, through `50-L`.
The authoritative instance selection is in `Filenames/`; do not infer the
benchmark from the number of files present under `2016/Ins/`.

The finalized comparison workbook is `2016/results/Comparison.xlsx`. Its
displayed solver groups map to the six raw workbooks above. The three 10-job S
rows named `10_10_005_100_{25,50,75}` use `_2` replicas; the corresponding
10-job L rows remain on `_1` replicas.

## Running From The Repository Root

All methods are launched through the shared batch runner, not by executing the
module file directly:

```text
python Test/run_batch_from_filelist.py --solvers directSAT
python Test/run_batch_from_filelist.py --solvers proposedSAT
python Test/run_batch_from_filelist.py --solvers cplex_mp
python Test/run_batch_from_filelist.py --solvers gurobi
python Test/run_batch_from_filelist.py --solvers cplex_cp
python Test/run_batch_from_filelist.py --solvers cpsat
```

For one instance, use `Test/run_single_instance.py` with the desired solver ID:

```text
python Test/run_single_instance.py 2016/Ins/wtrd_pred10/S/<instance>.GSP --solver directSAT --timeout 300
```

The runner applies `common/schedule_utils.py::window_tightening()` and writes
new workbooks to this directory and schedules to the solution tree listed
above.

> [!WARNING]
> `proposedSAT` must receive release dates and hard deadlines after
> `window_tightening()`. Use the shared runners for normal execution. Direct
> calls to `Encoding/proposedSAT.py` must apply the same preprocessing first.

## Statuses

- `FINISHED`: completed optimization result.
- `UNSAT` or `INFEASIBLE`: no feasible schedule was certified.
- `TIMEOUT`: the batch reporting limit was reached; a stored schedule is only an incumbent unless certified separately.
- `TIME_LIMIT_FEASIBLE`: an internal solver found an incumbent at its limit; the batch runner records it as `TIMEOUT`.

`Lmax` is recomputed as `max(C_j - d_j)` during validation. Run
`python Test/validate_workbook_results.py` to produce
`2016/results/validation_report.xlsx`, which checks status markers, schedules,
raw windows, no-overlap, precedence, and objective consistency.

`2016/results/sat_hard_constraint_stats.xlsx` contains base hard-CNF variable
and clause counts for `directSAT` and `proposedSAT`. Incremental objective
clauses are intentionally excluded.

## Runtime stability spot check

Due to time constraints, we selected only instances whose maximum baseline runtime across the six methods in `Comparison.xlsx` did not exceed 5 seconds. Each of the six solvers (`directSAT`, `proposedSAT`, `cplex_mp`, `gurobi`, `cplex_cp`, and `cpsat`) was run five times per instance, for 5,370 runs total.

The feasible cohort produced 5,250/5,250 `FINISHED` runs; all 5,250/5,250 rerun `Lmax` values matched the corresponding workbook value; and all six solvers agreed on the objective for 175/175 feasible instances. For the infeasible cohort, 120/120 expected `UNSAT`/`INFEASIBLE` statuses were reproduced. There were no failures or `TIMEOUT`s.

For each solver-instance group, the five rerun elapsed times were averaged and that mean was compared with the corresponding solver time in `Comparison.xlsx`. `ratio = five-run mean / baseline`; `APD = abs(five-run mean - baseline) / baseline`. The table reports the median signed delta in seconds, median ratio, median absolute percentage difference (APD), P90 APD, and the count (percentage) of groups within each APD threshold. APD percentiles use linear/type-7 interpolation. Within-instance CV is secondary evidence about repeat-to-repeat spread: it is the sample standard deviation divided by the five-run mean, summarized by its median across 179 groups.

| Solver | Median signed delta (s) | Median ratio | Median APD | P90 APD | Within ±10% | Within ±25% | Within ±50% | Median CV |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `directSAT` | +0.105 | 1.177x | 17.7% | 31.1% | 52 (29.1%) | 125 (69.8%) | 179 (100%) | 1.7% |
| `proposedSAT` | +0.071 | 1.176x | 17.8% | 26.7% | 26 (14.5%) | 149 (83.2%) | 178 (99.4%) | 2.6% |
| `cplex_mp` | +0.040 | 1.052x | 5.4% | 11.6% | 148 (82.7%) | 179 (100%) | 179 (100%) | 1.7% |
| `gurobi` | -0.043 | 0.928x | 7.4% | 16.4% | 119 (66.5%) | 174 (97.2%) | 178 (99.4%) | 2.2% |
| `cplex_cp` | -0.022 | 0.955x | 5.4% | 19.5% | 124 (69.3%) | 174 (97.2%) | 179 (100%) | 2.6% |
| `cpsat` | +0.021 | 1.050x | 5.8% | 12.5% | 144 (80.4%) | 179 (100%) | 179 (100%) | 2.9% |

`cplex_mp` and `cpsat` show the closest typical runtime agreement with baseline (about 5–6% median APD). `cplex_cp` has a similar median but a broader P90 APD, while `gurobi` is about 7.4%; both SAT encodings reran about 17.7–17.8% slower at the median. Median within-instance CV is only 1.7–2.9%, so the five repetitions are internally tight even when shifted from the historical baseline.

PAR-10 stability analysis uses 3,000 s for uncertified rows. All 179 selected instances retained their certified outcomes/statuses in every rerun, so cohort PAR-10 is mean runtime and no cohort penalty term applies.

| Solver | Cohort baseline PAR-10 (s) | Rerun cohort PAR-10 (s) | Cohort change (%) | Full baseline PAR-10 (s) | Full sensitivity estimate (s) | Full change (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `directSAT` | 1.300 | 1.511 | +16.2% | 810.533 | 810.639 | +0.013% |
| `proposedSAT` | 0.408 | 0.464 | +13.9% | 249.825 | 249.853 | +0.011% |
| `cplex_mp` | 0.847 | 0.888 | +5.0% | 421.163 | 421.184 | +0.005% |
| `gurobi` | 0.703 | 0.656 | -6.6% | 210.469 | 210.446 | -0.011% |
| `cplex_cp` | 0.506 | 0.470 | -7.1% | 0.517 | 0.498 | -3.517% |
| `cpsat` | 0.428 | 0.446 | +4.2% | 0.438 | 0.447 | +2.049% |

Cohort percentages can look material because runtimes are subsecond, but absolute shifts are at most 0.211 s. In the full-benchmark estimate, Direct SAT, Proposed SAT, MIP, and Gurobi changes are negligible because 3,000-s penalties dominate; `cplex_cp` and `cpsat` change by about 3.5% and 2.0%, respectively, but only 0.018 s and 0.009 s in absolute terms, and the solver ranking is unchanged. No solver certification count or outcome changed: only measured-time terms changed, not PAR-10 penalty terms.

Raw records: [`runtime_stability_subset.csv`](runtime_stability_subset.csv).
