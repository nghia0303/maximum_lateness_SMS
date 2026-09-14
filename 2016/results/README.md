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
