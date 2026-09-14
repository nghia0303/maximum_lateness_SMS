"""
Solve the Single Machine Scheduling Problem with Precedence Constraints using
IBM CPLEX MP through DOcplex with a time-indexed formulation.

This module is intentionally present even when CPLEX is not installed. Missing
Python packages or CPLEX runtime/license issues are returned as explicit solver
statuses so batch runs can record the environment limitation.
"""

from pathlib import Path
import os
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.dataset import read_dataset
from common.schedule_utils import compute_max_lateness, window_tightening


def solve_with_cplex_mp(n, durations, ready_dates, due_dates, deadlines, successors, time_limit=300):
    try:
        from docplex.mp.model import Model
    except ImportError:
        return None, "STATUS_MISSING_DOCPLEX_MP", False, 0, None

    jobs = range(1, n + 1)
    valid_starts = {
        job: list(range(ready_dates[job], deadlines[job] - durations[job] + 1))
        for job in jobs
    }
    if any(not starts for starts in valid_starts.values()):
        return None, "INFEASIBLE", False, 0, None

    try:
        model = Model(name="SingleMachineScheduling_CPLEX_MP", log_output=False)
        model.parameters.timelimit = time_limit
        model.parameters.threads = max(1, (os.cpu_count() or 2) // 2)

        x = {
            (job, start): model.binary_var(name=f"x_{job}_{start}")
            for job in jobs
            for start in valid_starts[job]
        }
        lmax = model.integer_var(lb=-model.infinity, name="Lmax")

        start_expr = {
            job: model.sum(start * x[job, start] for start in valid_starts[job])
            for job in jobs
        }

        for job in jobs:
            model.add_constraint(
                model.sum(x[job, start] for start in valid_starts[job]) == 1,
                ctname=f"start_once_{job}",
            )

        earliest_time = min(ready_dates.values())
        latest_time = max(deadlines.values())
        for time_point in range(earliest_time, latest_time):
            active_literals = []
            for job in jobs:
                lower = max(ready_dates[job], time_point - durations[job] + 1)
                upper = min(time_point, deadlines[job] - durations[job])
                for start in range(lower, upper + 1):
                    active_literals.append(x[job, start])
            if active_literals:
                model.add_constraint(model.sum(active_literals) <= 1, ctname=f"capacity_{time_point}")

        for job in jobs:
            for successor in successors.get(job, []):
                model.add_constraint(
                    start_expr[job] + durations[job] <= start_expr[successor],
                    ctname=f"prec_{job}_{successor}",
                )

        for job in jobs:
            model.add_constraint(
                lmax >= start_expr[job] + durations[job] - due_dates[job],
                ctname=f"lmax_{job}",
            )

        model.minimize(lmax)
        solution = model.solve(log_output=False)
        solve_time = float(getattr(model.solve_details, "time", 0) or 0)

        if solution is not None:
            schedule = {
                job: int(
                    round(
                        sum(start * float(solution.get_value(x[job, start])) for start in valid_starts[job])
                    )
                )
                for job in jobs
            }
            objective = compute_max_lateness(
                schedule, durations, due_dates, clamp_zero=False
            )
            gap = getattr(model.solve_details, "mip_relative_gap", None)
            gap_percent = None if gap is None else float(gap) * 100
            status_name = str(getattr(model.solve_details, "status", "")).lower()
            if gap_percent is not None and gap_percent > 0:
                return schedule, objective, "TIME_LIMIT_FEASIBLE", solve_time, gap_percent
            if "time" in status_name and gap_percent is None:
                return schedule, objective, "TIME_LIMIT_FEASIBLE", solve_time, None
            return schedule, objective, True, solve_time, 0.0

        status_name = str(getattr(model.solve_details, "status", "STATUS_NO_SOLUTION"))
        if "infeasible" in status_name.lower():
            return None, "INFEASIBLE", False, solve_time, None
        if "time" in status_name.lower():
            return None, "TIMEOUT", False, solve_time, None
        return None, f"STATUS_{status_name.replace(' ', '_').upper()}", False, solve_time, None
    except Exception as exc:
        status = type(exc).__name__.upper()
        return None, f"STATUS_CPLEX_MP_{status}", False, 0, None


def solve_MIP(n, durations, ready_dates, due_dates, deadlines, successors, time_limit=300):
    return solve_with_cplex_mp(n, durations, ready_dates, due_dates, deadlines, successors, time_limit)
