"""
Solve the Single Machine Scheduling Problem with Precedence Constraints using
IBM CP Optimizer through DOcplex CP.

This module can be imported without a working CP Optimizer installation. Runtime
or license failures are returned as explicit statuses for experiment logs.
"""

import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.dataset import read_dataset
from common.schedule_utils import compute_max_lateness, window_tightening


def solve_with_cplex_cp(n, durations, ready_dates, due_dates, deadlines, successors, time_limit=300):
    try:
        from docplex.cp.model import CpoModel
        from docplex.cp.expression import interval_var
        from docplex.cp.modeler import end_before_start, end_of, max as cp_max, minimize, no_overlap
    except ImportError:
        return None, "STATUS_MISSING_DOCPLEX_CP", False, 0, None

    jobs = range(1, n + 1)
    for job in jobs:
        if deadlines[job] - durations[job] < ready_dates[job]:
            return None, "INFEASIBLE", False, 0, None

    try:
        model = CpoModel(name="SingleMachineScheduling_CPLEX_CP")
        intervals = {
            job: interval_var(
                start=(ready_dates[job], deadlines[job] - durations[job]),
                size=durations[job],
                name=f"I_{job}",
            )
            for job in jobs
        }

        model.add(no_overlap([intervals[job] for job in jobs]))

        for job in jobs:
            for successor in successors.get(job, []):
                model.add(end_before_start(intervals[job], intervals[successor]))

        lateness_terms = [end_of(intervals[job]) - due_dates[job] for job in jobs]
        model.add(minimize(cp_max(lateness_terms)))

        result = model.solve(
            TimeLimit=time_limit,
            Workers=max(1, (os.cpu_count() or 2) // 2),
            LogVerbosity="Quiet",
        )
        solve_time = float(result.get_solve_time() or 0)
        status_name = str(result.get_solve_status())

        if result and result.is_solution():
            schedule = {job: int(result.get_var_solution(intervals[job]).get_start()) for job in jobs}
            objective = compute_max_lateness(
                schedule, durations, due_dates, clamp_zero=False
            )
            if status_name == "Optimal":
                return schedule, objective, True, solve_time, 0.0
            return schedule, objective, "TIME_LIMIT_FEASIBLE", solve_time, None

        if status_name == "Infeasible":
            return None, "INFEASIBLE", False, solve_time, None
        if status_name in {"Unknown", "SearchStopped", "SearchHasNotStarted"}:
            return None, "TIMEOUT", False, solve_time, None
        return None, f"STATUS_CPLEX_CP_{status_name.upper()}", False, solve_time, None
    except Exception as exc:
        status = type(exc).__name__.upper()
        return None, f"STATUS_CPLEX_CP_{status}", False, 0, None


def solve_MIP(n, durations, ready_dates, due_dates, deadlines, successors, time_limit=300):
    return solve_with_cplex_cp(n, durations, ready_dates, due_dates, deadlines, successors, time_limit)
