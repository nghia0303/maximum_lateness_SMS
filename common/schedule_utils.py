from collections import deque


def build_predecessors(job_count, successors):
    predecessors = {job: [] for job in range(1, job_count + 1)}
    for job in range(1, job_count + 1):
        for successor in successors.get(job, []):
            predecessors[successor].append(job)
    return predecessors


def window_tightening(job_count, ready_dates, durations, deadlines, successors):
    predecessors = build_predecessors(job_count, successors)

    indegree = {job: len(predecessors[job]) for job in range(1, job_count + 1)}
    queue = deque(job for job in range(1, job_count + 1) if indegree[job] == 0)
    topological_order = []

    while queue:
        job = queue.popleft()
        topological_order.append(job)
        for successor in successors[job]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)

    if len(topological_order) != job_count:
        raise ValueError("Precedence graph has a cycle!")

    tightened_ready_dates = {job: ready_dates[job] for job in range(1, job_count + 1)}
    for job in topological_order:
        if predecessors[job]:
            tightened_ready_dates[job] = max(
                ready_dates[job],
                max(tightened_ready_dates[parent] + durations[parent] for parent in predecessors[job]),
            )

    tightened_deadlines = {job: deadlines[job] for job in range(1, job_count + 1)}
    for job in reversed(topological_order):
        if successors[job]:
            tightened_deadlines[job] = min(
                tightened_deadlines[job],
                min(tightened_deadlines[successor] - durations[successor] for successor in successors[job]),
            )

    return tightened_ready_dates, tightened_deadlines


def bfs_distances(start_job, adjacency):
    distances = {start_job: 0}
    queue = deque([start_job])

    while queue:
        job = queue.popleft()
        for next_job in adjacency.get(job, []):
            if next_job not in distances:
                distances[next_job] = distances[job] + 1
                queue.append(next_job)

    return distances


def source_to_sink_endpoint_edges(job_count, successors):
    predecessors = build_predecessors(job_count, successors)
    sources = [job for job in range(1, job_count + 1) if not predecessors[job]]
    sinks = [job for job in range(1, job_count + 1) if not successors.get(job, [])]
    extra_edges = set()

    for source in sources:
        distances = bfs_distances(source, successors)
        for sink in sinks:
            if distances.get(sink, -1) >= 2 and sink not in successors.get(source, []):
                extra_edges.add((source, sink))

    return extra_edges


def all_ancestors_to_sink_endpoint_edges(job_count, successors):
    predecessors = build_predecessors(job_count, successors)
    sinks = [job for job in range(1, job_count + 1) if not successors.get(job, [])]
    extra_edges = set()

    for sink in sinks:
        distances = bfs_distances(sink, predecessors)
        for ancestor, distance in distances.items():
            if distance >= 2 and sink not in successors.get(ancestor, []):
                extra_edges.add((ancestor, sink))

    return extra_edges


def extend_successors(job_count, successors, extra_edges):
    extended_successors = {
        job: list(successors.get(job, []))
        for job in range(1, job_count + 1)
    }

    for start_job, end_job in sorted(extra_edges):
        if end_job not in extended_successors[start_job]:
            extended_successors[start_job].append(end_job)

    for job in range(1, job_count + 1):
        extended_successors[job].sort()

    return extended_successors


def compute_max_lateness(schedule, durations, due_dates, clamp_zero=False):
    if not schedule:
        return 0

    lateness_values = []
    for job, start_time in schedule.items():
        completion_time = start_time + durations[job]
        lateness = completion_time - due_dates[job]
        lateness_values.append(max(0, lateness) if clamp_zero else lateness)

    return max(lateness_values)


def compute_job_lateness(schedule, durations, due_dates):
    lateness_by_job = {}
    for job, start_time in schedule.items():
        completion_time = start_time + durations[job]
        lateness_by_job[job] = completion_time - due_dates[job]
    return lateness_by_job


def format_solution_text(schedule, durations, due_dates, lmax, solve_time=None, gap=None):
    lateness_by_job = compute_job_lateness(schedule, durations, due_dates)
    matching_jobs = [job for job, lateness in lateness_by_job.items() if lateness == lmax]
    if not matching_jobs and lateness_by_job:
        max_lateness = max(lateness_by_job.values())
        matching_jobs = [job for job, lateness in lateness_by_job.items() if lateness == max_lateness]

    lmax_suffix = ""
    if matching_jobs:
        label = "Job" if len(matching_jobs) == 1 else "Jobs"
        job_list = ", ".join(str(job) for job in sorted(matching_jobs))
        lmax_suffix = f" ({label} {job_list})"
    lines = [f"Lmax = {lmax}{lmax_suffix}"]

    if gap is not None and gap > 0:
        lines.append(f"MIP Gap = {gap:.2f}%")
    if solve_time is not None:
        lines.append(f"Solve Time = {solve_time:.2f}s")

    lines.append("Schedule:")
    for job, start in sorted(schedule.items(), key=lambda item: item[1]):
        end = start + durations[job]
        lines.append(
            f"  Job {job}: start = {start}, end = {end}, due_date = {due_dates[job]}, lateness = {lateness_by_job[job]}"
        )

    return "\n".join(lines) + "\n"


def validate_schedule(schedule, job_count, durations, ready_dates, deadlines, successors):
    violations = []

    for job in range(1, job_count + 1):
        if job not in schedule:
            violations.append(f"[C1] Job {job} is not scheduled")

    if violations:
        return False, violations

    if len(schedule) != job_count:
        violations.append(f"[C4] So job trong schedule ({len(schedule)}) != n ({job_count})")
        return False, violations

    for job, start_time in schedule.items():
        if job not in durations:
            violations.append(f"[C2] Job {job} is missing from the instance data")
            continue

        completion_time = start_time + durations[job]
        if start_time < ready_dates[job]:
            violations.append(f"[C2] Job {job}: start={start_time} < ready_date={ready_dates[job]}")
        if completion_time > deadlines[job]:
            violations.append(f"[C2] Job {job}: end={completion_time} > deadline={deadlines[job]}")

    intervals = []
    for job, start_time in schedule.items():
        intervals.append((start_time, start_time + durations[job], job))
    intervals.sort()

    for index in range(len(intervals) - 1):
        start_a, end_a, job_a = intervals[index]
        start_b, end_b, job_b = intervals[index + 1]
        if end_a > start_b:
            violations.append(
                f"[C3] Overlap: Job {job_a} [{start_a}, {end_a}) va Job {job_b} [{start_b}, {end_b})"
            )

    for job in range(1, job_count + 1):
        finish_time = schedule[job] + durations[job]
        for successor in successors[job]:
            if successor not in schedule:
                violations.append(f"[C5] Job {job} has successor {successor}, but job {successor} is not scheduled")
                continue
            if finish_time > schedule[successor]:
                violations.append(
                    f"[C5] Precedence violation: {job} -> {successor}, but finish({job})={finish_time} > start({successor})={schedule[successor]}"
                )

    return len(violations) == 0, violations
