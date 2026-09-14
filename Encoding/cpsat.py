"""
Solve the Single Machine Scheduling Problem with Precedence Constraints using
OR-Tools CP-SAT.

Formulation:
- start/end/interval variables for each job
- one NoOverlap constraint for the single machine
- direct precedence constraints end_i <= start_j
- true Lmax objective: minimize max(end_j - due_j)
"""

from pathlib import Path
import os
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.dataset import read_dataset
from common.schedule_utils import compute_max_lateness, window_tightening


def solve_with_cpsat(n, durations, ready_dates, due_dates, deadlines, successors, time_limit=300):
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        return None, "STATUS_MISSING_ORTOOLS", False, 0, None

    model = cp_model.CpModel()
    jobs = range(1, n + 1)

    starts = {}
    ends = {}
    intervals = []

    for job in jobs:
        last_start = deadlines[job] - durations[job]
        if last_start < ready_dates[job]:
            return None, "INFEASIBLE", False, 0, None

        starts[job] = model.NewIntVar(ready_dates[job], last_start, f"start_{job}")
        ends[job] = model.NewIntVar(ready_dates[job] + durations[job], deadlines[job], f"end_{job}")
        intervals.append(model.NewIntervalVar(starts[job], durations[job], ends[job], f"interval_{job}"))

    model.AddNoOverlap(intervals)

    for job in jobs:
        for successor in successors.get(job, []):
            model.Add(ends[job] <= starts[successor])

    lmax_lb = min(ready_dates[job] + durations[job] - due_dates[job] for job in jobs)
    lmax_ub = max(deadlines[job] - due_dates[job] for job in jobs)
    lmax = model.NewIntVar(lmax_lb, lmax_ub, "Lmax")
    for job in jobs:
        model.Add(lmax >= ends[job] - due_dates[job])
    model.Minimize(lmax)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_search_workers = max(1, (os.cpu_count() or 2) // 2)

    status = solver.Solve(model)
    solve_time = solver.WallTime()

    if status == cp_model.OPTIMAL:
        schedule = {job: int(solver.Value(starts[job])) for job in jobs}
        objective = compute_max_lateness(
            schedule, durations, due_dates, clamp_zero=False
        )
        return schedule, objective, True, solve_time, 0.0

    if status == cp_model.FEASIBLE:
        schedule = {job: int(solver.Value(starts[job])) for job in jobs}
        objective = compute_max_lateness(
            schedule, durations, due_dates, clamp_zero=False
        )
        return schedule, objective, "TIME_LIMIT_FEASIBLE", solve_time, None

    if status == cp_model.INFEASIBLE:
        return None, "INFEASIBLE", False, solve_time, None

    return None, "TIMEOUT", False, solve_time, None


def solve_MIP(n, durations, ready_dates, due_dates, deadlines, successors, time_limit=300):
    return solve_with_cpsat(n, durations, ready_dates, due_dates, deadlines, successors, time_limit)
