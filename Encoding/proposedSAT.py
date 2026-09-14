"""Proposed cumulative-start SAT encoding without the source-ready anchor."""

from pathlib import Path
import sys

from pysat.formula import CNF
from pysat.solvers import Solver


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.dataset import read_dataset
from common.schedule_utils import compute_max_lateness, format_solution_text, validate_schedule as shared_validate_schedule, window_tightening


def layer_one_jobs(n, successors):
    indegree = {job: 0 for job in range(1, n + 1)}
    for job in range(1, n + 1):
        for successor in successors.get(job, []):
            if successor in indegree:
                indegree[successor] += 1
    return [job for job in range(1, n + 1) if indegree[job] == 0]


def _l_at_most(L, job, time_point, valid_starts):
    times = valid_starts[job]
    if time_point < times[0]:
        return False
    if time_point >= times[-1]:
        return True
    return L[(job, time_point)]


def _not_l_at_most(L, job, time_point, valid_starts):
    value = _l_at_most(L, job, time_point, valid_starts)
    if value is True:
        return False
    if value is False:
        return True
    return -value


def _append_simplified_clause(cnf, base_literals, optional_literals):
    clause = list(base_literals)
    for lit in optional_literals:
        if lit is True:
            return False
        if lit is False:
            continue
        clause.append(lit)
    cnf.append(clause)
    return True


def _build_hard_cnf(
    n,
    durations,
    ready_dates,
    deadlines,
    successors,
    verbose=False,
    contradiction_on_impossible=False,
    include_source_ready_anchor=True,
):
    """Build the hard CNF using the same encoding path used by the solver."""
    jobs = list(range(1, n + 1))
    cnf = CNF()
    var_counter = 1
    S = {}
    L = {}
    valid_starts = {}

    for i in jobs:
        last_start = deadlines[i] - durations[i]
        if last_start < ready_dates[i]:
            if verbose:
                print(f"Job {i} impossible: last_start < ready ({last_start} < {ready_dates[i]})")
            if contradiction_on_impossible:
                valid_starts[i] = []
                continue
            return None, None, None, None, None, False

        valid_starts[i] = list(range(ready_dates[i], last_start + 1))
        for t in valid_starts[i]:
            S[(i, t)] = var_counter
            var_counter += 1

    if verbose:
        print(f"Created S variables: {len(S)}. Next var id = {var_counter}")

    l_count = 0
    l_clauses = 0

    for j in jobs:
        times = valid_starts[j]
        if not times:
            if contradiction_on_impossible:
                cnf.append([])
                l_clauses += 1
            continue

        t_min = times[0]
        t_max = times[-1]
        for t in range(t_min, t_max + 1):
            L[(j, t)] = var_counter
            var_counter += 1
            l_count += 1

        cnf.append([L[(j, t_max)]])
        cnf.append([-L[(j, t_min)], S[(j, t_min)]])
        l_clauses += 2

        for t in range(t_min, t_max + 1):
            cnf.append([L[(j, t)], -S[(j, t)]])
            l_clauses += 1

        for t in range(t_min + 1, t_max + 1):
            cnf.append([-S[(j, t)], -L[(j, t - 1)]])
            cnf.append([L[(j, t)], -L[(j, t - 1)]])
            cnf.append([-L[(j, t)], L[(j, t - 1)], S[(j, t)]])
            l_clauses += 3

    if verbose:
        print("L variables:", l_count)
        print("L clauses:", l_clauses)

    no_overlap_clauses = 0

    for i_index, i in enumerate(jobs):
        for j in jobs[i_index + 1 :]:
            if not valid_starts[i] or not valid_starts[j]:
                continue
            for t_i in valid_starts[i]:
                left = _l_at_most(L, j, t_i - durations[j], valid_starts)
                right = _not_l_at_most(L, j, t_i + durations[i] - 1, valid_starts)
                appended = _append_simplified_clause(
                    cnf,
                    [-S[(i, t_i)]],
                    [left, right],
                )
                if appended:
                    no_overlap_clauses += 1

    prec_clauses = 0

    for i in jobs:
        for j in successors.get(i, []):
            if not valid_starts[i] or not valid_starts[j]:
                continue
            t_min_j = valid_starts[j][0]
            t_max_j = valid_starts[j][-1]

            for t_i in valid_starts[i]:
                finish = t_i + durations[i] - 1
                if finish < t_min_j or finish > t_max_j:
                    continue
                cnf.append([-S[(i, t_i)], -L[(j, finish)]])
                prec_clauses += 1

    source_ready_anchor_clause = []
    if include_source_ready_anchor:
        for job in layer_one_jobs(n, successors):
            ready_time = ready_dates[job]
            if (job, ready_time) in S:
                source_ready_anchor_clause.append(S[(job, ready_time)])
        if source_ready_anchor_clause:
            cnf.append(source_ready_anchor_clause)

    if verbose:
        print("Precedence clauses:", prec_clauses)
        print("Pairwise no-overlap clauses:", no_overlap_clauses)
        print("Source-ready anchor jobs:", layer_one_jobs(n, successors))
        print("Source-ready anchor literals:", len(source_ready_anchor_clause))
        print("Total clauses:", len(cnf.clauses))
        print("Total variables:", var_counter - 1)
        primary_vars = list(S.values()) + list(L.values())
        assert len(primary_vars) == len(set(primary_vars)), "Duplicate primary SAT variable IDs detected"

    build_stats = {
        "total_variables": var_counter - 1,
        "total_clauses": len(cnf.clauses),
    }

    return cnf, valid_starts, S, L, build_stats, True


def count_hard_cnf(n, durations, ready_dates, deadlines, successors):
    """Count the same hard CNF as ver5 without solving."""
    _, _, _, _, build_stats, _ = _build_hard_cnf(
        n,
        durations,
        ready_dates,
        deadlines,
        successors,
        contradiction_on_impossible=True,
        include_source_ready_anchor=False,
    )
    return build_stats["total_variables"], build_stats["total_clauses"]


def solve_SAT(
    n,
    durations,
    ready_dates,
    deadlines,
    successors,
    verbose=False,
    sat_solver_name="g421",
):
    """Solve feasibility and return the live solver for objective tightening."""
    cnf, valid_starts, S, L, _, build_status = _build_hard_cnf(
        n,
        durations,
        ready_dates,
        deadlines,
        successors,
        verbose=verbose,
        include_source_ready_anchor=False,
    )
    if not build_status:
        return None, None, None, None, None, False, None

    print("\n=== SOLVING (HARD CONSTRAINTS ONLY) ===")
    if verbose:
        print("SAT backend:", sat_solver_name)
    solver = Solver(name=sat_solver_name, bootstrap_with=cnf)
    is_sat = solver.solve()

    if not is_sat:
        if verbose:
            print("UNSAT -- no feasible schedule.")
        solver.delete()
        return None, None, None, None, None, is_sat, None

    raw_model = solver.get_model()
    assert raw_model is not None, "Solver returned SAT but model is None"
    model = set(raw_model)

    schedule = {}
    for (i, t), vid in S.items():
        if vid in model:
            schedule[i] = t

    if verbose:
        print("Feasible schedule found")

    return cnf, schedule, valid_starts, S, L, is_sat, solver


def validate_schedule(schedule, durations, ready_dates, deadlines, successors):
    _, violations = shared_validate_schedule(
        schedule,
        len(durations),
        durations,
        ready_dates,
        deadlines,
        successors,
    )
    return violations


def compute_UB_Lmax(schedule, durations, due_dates):
    return compute_max_lateness(schedule, durations, due_dates, clamp_zero=False)


def incremental_SAT_Lmax(
    durations,
    due_dates,
    S,
    L,
    solver,
    UB,
    sol_file,
    valid_starts,
    verbose=False,
):
    """Tighten the objective using the live solver from solve_SAT."""
    iteration_count = 0
    var_to_S = {v: (i, t) for (i, t), v in S.items()}

    print("\n=== SOLVING INCREMENTAL SAT (SINGLE SOLVER) ===")

    while True:
        iteration_count += 1
        if verbose:
            print("\n==============================")
            print("Trying with Lmax UB =", UB)
            print("Iteration:", iteration_count)

        for j in range(1, len(durations) + 1):
            latest_start = due_dates[j] + UB - durations[j] - 1
            if latest_start < valid_starts[j][0]:
                solver.add_clause([])
            elif latest_start < valid_starts[j][-1]:
                solver.add_clause([L[(j, latest_start)]])

        if solver.solve():
            if verbose:
                print("SAT")
            raw_model = solver.get_model()
            assert raw_model is not None, "Solver returned SAT but model is None"
            best_schedule = {}

            for var in raw_model:
                if var > 0 and var in var_to_S:
                    i, t = var_to_S[var]
                    best_schedule[i] = t

            lmax = compute_UB_Lmax(best_schedule, durations, due_dates)

            if verbose:
                print("New Lmax UB:", lmax)
                if UB == lmax:
                    print("Warning: UB not decreasing, possible bug.")

            UB = lmax
            with open(sol_file, "w", encoding="utf-8") as handle:
                handle.write(format_solution_text(best_schedule, durations, due_dates, UB))
                handle.flush()
        else:
            if verbose:
                print("UNSAT")
            break

    stats = solver.accum_stats()
    solver.delete()

    if verbose:
        with open(sol_file, "a", encoding="utf-8") as handle:
            handle.write(
                f"STATS "
                f"conflicts={stats.get('conflicts', 0)} "
                f"decisions={stats.get('decisions', 0)} "
                f"propagations={stats.get('propagations', 0)} "
                f"restarts={stats.get('restarts', 0)}\n"
            )
        print(
            f"SAT stats — iterations: {iteration_count}, "
            f"conflicts: {stats.get('conflicts', 0)}, "
            f"decisions: {stats.get('decisions', 0)}, "
            f"propagations: {stats.get('propagations', 0)}, "
            f"restarts: {stats.get('restarts', 0)}"
        )

    print("Incremental SAT finished.")
    print("Best Lmax UB found:", UB)
    return UB
