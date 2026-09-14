"""
Solve the Single Machine Scheduling Problem with Precedence Constraints using
Gurobi MIP with a time-indexed formulation.
"""

import math
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.dataset import read_dataset
from common.schedule_utils import compute_max_lateness, window_tightening


def _true_lmax(schedule, durations, due_dates):
    return compute_max_lateness(schedule, durations, due_dates, clamp_zero=False)


def _true_gap_percent(model, incumbent_lmax):
    """Compute a gap against the extracted schedule objective when possible."""
    try:
        objective_bound = float(model.ObjBound)
    except (AttributeError, TypeError, ValueError):
        return None

    if not math.isfinite(objective_bound):
        return None

    numerator = max(0.0, float(incumbent_lmax) - objective_bound)
    denominator = max(1.0, abs(float(incumbent_lmax)))
    return numerator / denominator * 100.0


def solve_with_gurobi(n, durations, ready_dates, due_dates, deadlines, successors, time_limit=300):
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError:
        return None, "STATUS_MISSING_GUROBIPY", False, 0, None

    jobs = range(1, n + 1)
    valid_starts = {
        job: list(range(ready_dates[job], deadlines[job] - durations[job] + 1))
        for job in jobs
    }
    if any(not starts for starts in valid_starts.values()):
        return None, "INFEASIBLE", False, 0, None

    try:
        model = gp.Model("SingleMachineScheduling_TimeIndexed")
        model.setParam("OutputFlag", 0)
        model.setParam("TimeLimit", time_limit)
        model.setParam("DualReductions", 0)
        model.setParam("Threads", max(1, (os.cpu_count() or 2) // 2))

        x = model.addVars(
            ((job, start) for job in jobs for start in valid_starts[job]),
            vtype=GRB.BINARY,
            name="x",
        )
        lmax = model.addVar(vtype=GRB.INTEGER, name="Lmax", lb=-GRB.INFINITY)

        start_expr = {
            job: gp.quicksum(start * x[job, start] for start in valid_starts[job])
            for job in jobs
        }

        for job in jobs:
            model.addConstr(
                gp.quicksum(x[job, start] for start in valid_starts[job]) == 1,
                name=f"start_once_{job}",
            )

        earliest_time = min(ready_dates.values())
        latest_time = max(deadlines.values())
        for time_point in range(earliest_time, latest_time):
            active_terms = []
            for job in jobs:
                lower = max(ready_dates[job], time_point - durations[job] + 1)
                upper = min(time_point, deadlines[job] - durations[job])
                for start in range(lower, upper + 1):
                    active_terms.append(x[job, start])
            if active_terms:
                model.addConstr(gp.quicksum(active_terms) <= 1, name=f"capacity_{time_point}")

        for job in jobs:
            for successor in successors.get(job, []):
                model.addConstr(
                    start_expr[job] + durations[job] <= start_expr[successor],
                    name=f"prec_{job}_{successor}",
                )

        for job in jobs:
            model.addConstr(
                lmax >= start_expr[job] + durations[job] - due_dates[job],
                name=f"lmax_{job}",
            )

        model.setObjective(lmax, GRB.MINIMIZE)
        model.optimize()

        solve_time = model.Runtime
        if model.status == GRB.OPTIMAL:
            schedule = _extract_schedule(valid_starts, x)
            objective = _true_lmax(schedule, durations, due_dates)
            return schedule, objective, True, solve_time, 0.0

        if model.status == GRB.TIME_LIMIT:
            if model.SolCount > 0:
                schedule = _extract_schedule(valid_starts, x)
                objective = _true_lmax(schedule, durations, due_dates)
                gap = _true_gap_percent(model, objective)
                if gap is not None and gap <= 0:
                    return schedule, objective, True, solve_time, 0.0
                return schedule, objective, "TIME_LIMIT_FEASIBLE", solve_time, gap
            return None, "TIMEOUT", False, solve_time, None

        if model.status == GRB.INFEASIBLE:
            return None, "INFEASIBLE", False, solve_time, None

        return None, f"STATUS_{model.status}", False, solve_time, None
    except gp.GurobiError as exc:
        error_code = getattr(exc, "errno", "ERROR")
        return None, f"STATUS_GUROBI_{error_code}", False, 0, None
    except Exception as exc:
        status = type(exc).__name__.upper()
        return None, f"STATUS_GUROBI_{status}", False, 0, None


def _extract_schedule(valid_starts, x_vars):
    schedule = {}
    for job, starts in valid_starts.items():
        selected_start = next((start for start in starts if x_vars[job, start].X > 0.5), None)
        if selected_start is None:
            selected_start = int(round(sum(start * x_vars[job, start].X for start in starts)))
        schedule[job] = int(selected_start)
    return schedule


def solve_MIP(n, durations, ready_dates, due_dates, deadlines, successors, time_limit=300):
    return solve_with_gurobi(n, durations, ready_dates, due_dates, deadlines, successors, time_limit)
