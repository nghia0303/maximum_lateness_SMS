# Single-Machine Scheduling with Precedence Constraints

This repository contains reproducible code and selected benchmark artifacts for
single-machine scheduling with release dates, hard deadlines, due dates, and
precedence constraints.

The objective is true maximum lateness:

```text
Lmax = max_j (C_j - d_j)
```


## Solver Implementations

The public code contains six solver IDs:

- `directSAT`: direct start-time SAT encoding with exactly-one constraints and pairwise conflicts.
- `proposedSAT`: cumulative-start SAT encoding using exact-start variables `S` and cumulative variables `L`.
- `cplex_mp`: time-indexed CPLEX MIP.
- `gurobi`: time-indexed Gurobi MIP.
- `cplex_cp`: IBM ILOG CP Optimizer interval model.
- `cpsat`: OR-Tools CP-SAT interval model.

All runners apply the shared topological release/deadline tightening before
building a model. The two SAT solvers use the PySAT `g421` backend and permanent
objective-cutoff clauses during incremental optimization.

The `Encoding/` directory contains exactly the six public solver modules listed
above. Each module is invoked through the shared runner rather than as a
standalone command-line program.

> [!WARNING]
> `proposedSAT` requires `window_tightening()` before model construction. The
> batch and single-instance runners apply this preprocessing automatically. If
> `Encoding/proposedSAT.py` is called directly, call `window_tightening()`
> first; otherwise precedence clauses for starts outside a successor's
> tightened window may be omitted.
>
> `directSAT` does not have this specific precedence-window precondition
> because it enumerates conflicting predecessor-successor start pairs directly.

## Method-to-Code Map

All public solver modules are invoked through the runners; they are not
standalone command-line programs. The common execution path is
`Test/runner_common.py::run_single_instance()`, which reads the instance,
applies `common/schedule_utils.py::window_tightening()`, dispatches the solver,
and writes the solution under `2016/solutions_{solver}/`.

| Method | Solver ID | Code entry point | Main model/backend |
| --- | --- | --- | --- |
| Direct SAT | `directSAT` | `Encoding/directSAT.py` | Exact-start SAT variables, Exactly-One sequential counter, pairwise conflicts; PySAT `g421` |
| Proposed SAT | `proposedSAT` | `Encoding/proposedSAT.py` | Exact-start plus cumulative-start SAT variables, no source-ready anchor; PySAT `g421` |
| MIP | `cplex_mp` | `Encoding/cplex_mp.py` | Time-indexed CPLEX MIP through DOcplex |
| MIP | `gurobi` | `Encoding/gurobi.py` | Time-indexed Gurobi MIP |
| CP | `cplex_cp` | `Encoding/cplex_cp.py` | IBM ILOG CP Optimizer interval model |
| CP | `cpsat` | `Encoding/cpsat.py` | OR-Tools CP-SAT interval model |

The Direct and Proposed SAT builders, one-solver lifecycle, and objective
cutoff logic are contained in their respective public modules. The MIP and CP
modules expose the runner-facing `solve_MIP()` function. Use the solver IDs
above in the commands below; do not import or execute old module names.

## Layout

```text
Encoding/       Solver modules and shared encoding builders
common/         Dataset parsing, preprocessing, validation, and paths
Filenames/      Authoritative benchmark filename lists
2016/Ins/       Selected .GSP benchmark instances
2016/           Solution trees and benchmark data
2016/results/   Result workbooks, comparison, validation, and CNF statistics
Test/           Batch runner, single-instance runner, and audit scripts
Test/validate_solutions.py
requirements.txt
```

The result catalogue is in `2016/results/README.md`. The workbooks remain at
`2016/results/results_{solver}.xlsx`, and schedules remain at
`2016/solutions_{solver}/{n}-{type}/` because these are the runtime paths used
by the runners.

## Environment

The recorded environment for the retained artifacts is:

- Python 3.12.10
- Windows 11
- Intel Core i5-14600KF
- 32 GB DDR4 RAM
- PySAT 1.9.dev7 with Glucose `g421` for the SAT runners
- OR-Tools 9.14.6206
- CPLEX 22.2.0.1 and docplex 2.32.264
- gurobipy 13.0.1
- pandas 3.0.1 and openpyxl 3.1.5
- 300 seconds per instance in the batch wrapper

Install Python dependencies with:

```text
python -m pip install -r requirements.txt
```

The MIP and CP solvers require separately installed and licensed commercial
software. No solver license, credential, or secret is included.

### Commercial Solver Setup

#### Gurobi

Install `gurobipy` and obtain a valid Gurobi license. Configure the license
outside this repository before running the Gurobi solver:

```powershell
$env:GRB_LICENSE_FILE = "C:\path\to\gurobi.lic"
python Test/run_batch_from_filelist.py --solvers gurobi
```

#### IBM CPLEX and CP Optimizer

Install IBM ILOG CPLEX Optimization Studio and ensure that the `cplex`,
`docplex`, and CP Optimizer runtime are available in the active Python
environment. A valid IBM license is required for both solvers:

```powershell
python Test/run_batch_from_filelist.py --solvers cplex_mp
python Test/run_batch_from_filelist.py --solvers cplex_cp
```

License files and credentials are not included in this repository. Follow the
installation and licensing instructions provided by Gurobi and IBM for the
relevant software version.

## Benchmark Selection

The default lane is `2016/Ins/`. The selected filelists contain 354 instances:
66 instances for 10 jobs and 72 instances for each of 20, 30, 40, and 50 jobs.
When `Filenames/{size}-{type}.txt` exists, it is authoritative for that type;
otherwise the runner falls back to `Filenames/{size}.txt`.


The `.GSP` files and their attribution or redistribution terms are separate
from the MIT license for the original code. See `2016/Ins/README.md` before
redistributing the benchmark data.

## Running

Run the two non-commercial SAT solvers by default:

```text
python Test/run_batch_from_filelist.py
```

Run selected solvers or only one instance type:

```text
python Test/run_batch_from_filelist.py --solvers directSAT
python Test/run_batch_from_filelist.py --solvers proposedSAT
python Test/run_batch_from_filelist.py --solvers cplex_mp
python Test/run_batch_from_filelist.py --solvers gurobi
python Test/run_batch_from_filelist.py --solvers cplex_cp
python Test/run_batch_from_filelist.py --solvers cpsat
python Test/run_batch_from_filelist.py --solvers directSAT proposedSAT
python Test/run_batch_from_filelist.py --solvers cplex_mp gurobi cplex_cp cpsat
python Test/run_batch_from_filelist.py --types S
```

Run one instance without persistent output:

```text
python Test/run_single_instance.py 2016/Ins/wtrd_pred10/S/<instance>.GSP --solver proposedSAT --timeout 300
```

Batch output is written to `2016/results/results_{solver}.xlsx` and
`2016/solutions_{solver}/`. A timeout row is recorded as `TIMEOUT` at the
configured 300-second reporting limit. A schedule found at a solver time limit
is an incumbent and is not an optimality certificate.

The finalized six-solver comparison workbook is `2016/results/Comparison.xlsx`.
The raw workbooks and solution trees listed in `2016/results/README.md` are the
underlying artifacts for the same filelist lane.

## Validation

Validate all retained workbooks and persisted schedules with:

```text
python Test/validate_workbook_results.py
```

The script reads the authoritative `Filenames/` lists and writes
`2016/results/validation_report.xlsx`. It checks status markers, schedule completeness,
raw release/deadline windows, single-machine non-overlap, precedence, and
recomputed true `Lmax`.

The standalone command validates one solution file:

```text
python Test/validate_solutions.py <instance.GSP> <solution.txt>
```

Hard CNF size statistics for `directSAT` and `proposedSAT` can be
regenerated with:

```text
python Test/count_sat_hard_constraints_for_workbook.py
```

The resulting `2016/results/sat_hard_constraint_stats.xlsx` counts base hard CNF only;
incremental objective clauses are excluded.

## Status Semantics

- `FINISHED`: an optimal result or a completed SAT optimization run.
- `UNSAT`: SAT proved that no feasible schedule exists.
- `INFEASIBLE`: a direct optimization solver proved infeasibility.
- `TIMEOUT`: the reporting limit was reached; any stored schedule is an incumbent unless separately certified.
- `TIME_LIMIT_FEASIBLE`: an internal solver returned a feasible incumbent at its time limit; the runner records it as `TIMEOUT`.

The included workbooks are artifacts from recorded runs. Runtime, status, and
objective comparisons should be made only after checking the validation report
and the exact solver, machine, timeout, and filelist provenance.

## License

Original code in this repository is released under the MIT License in
`LICENSE`. Benchmark data, Python packages, and commercial solver software are
subject to their own terms. The MIT License does not grant rights to those
third-party materials.
