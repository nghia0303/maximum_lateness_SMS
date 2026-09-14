"""
validate_solutions.py

Validate solution files against 5 constraints:
  1. Every job must be scheduled (must have a start time)
  2. Each start time must lie in [ready_date, deadline - duration]
  3. The single machine can process only one job at a time (no overlap)
  4. Each job must appear exactly once (the schedule must contain n jobs)
  5. Precedence constraints: if i ≺ j then finish_i <= start_j

Usage:
  python Test/validate_solutions.py <instance_path.GSP> <solution_path.txt>

Solution file format:
  Lmax = 10
  Schedule:
    Job 1: start = 5, end = 10
    Job 2: start = 10, end = 15
    ...
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.dataset import read_dataset
from common.schedule_utils import validate_schedule as shared_validate_schedule


def parse_solution(sol_path: Path) -> Dict[int, int]:
    """
    Parse solution file.
    
    Returns:
        dict {job_id: start_time}
        None if the file contains "UNSAT" or has an invalid format
    """
    if not sol_path.exists():
        return None

    content = sol_path.read_text(encoding="utf-8")
    if "UNSAT" in content:
        return None

    schedule = {}
    # Pattern: "Job 1: start = 5, end = 10"
    for line in content.splitlines():
        match = re.search(r"Job\s+(\d+):\s+start\s*=\s*(\d+)", line)
        if match:
            job_id = int(match.group(1))
            start_time = int(match.group(2))
            schedule[job_id] = start_time

    return schedule if schedule else None


def validate_schedule(
    schedule: Dict[int, int],
    n: int,
    durations: Dict[int, int],
    ready_dates: Dict[int, int],
    deadlines: Dict[int, int],
    successors: Dict[int, List[int]]
) -> Tuple[bool, List[str]]:
    """
    Validate 5 constraints.
    
    Returns:
        (is_valid: bool, violations: List[str])
    """
    return shared_validate_schedule(schedule, n, durations, ready_dates, deadlines, successors)


# ============================================================
# Main
# ============================================================

def main():
    if len(sys.argv) != 3:
        print("Usage: python Test/validate_solutions.py <instance.GSP> <solution.txt>")
        sys.exit(1)

    instance_path = Path(sys.argv[1])
    solution_path = Path(sys.argv[2])

    if not instance_path.exists():
        print(f"ERROR: Instance file not found: {instance_path}")
        sys.exit(1)

    if not solution_path.exists():
        print(f"ERROR: Solution file not found: {solution_path}")
        sys.exit(1)

    print("=" * 70)
    print("SOLUTION VALIDATION")
    print("=" * 70)
    print(f"Instance : {instance_path.name}")
    print(f"Solution : {solution_path.name}")
    print("-" * 70)

    # Read instance
    n, durations, ready_dates, due_dates, deadlines, successors = read_dataset(instance_path)
    print(f"Jobs (n) : {n}")

    # Parse solution
    schedule = parse_solution(solution_path)

    if schedule is None:
        print("\nResult   : UNSAT or invalid solution file")
        print("=" * 70)
        sys.exit(0)

    print(f"Scheduled: {len(schedule)} jobs")
    print("-" * 70)

    # Validate
    is_valid, violations = validate_schedule(
        schedule, n, durations, ready_dates, deadlines, successors
    )

    if is_valid:
        print("\nVALID - All constraints are satisfied!")
        print("\nChecked constraints:")
        print("  [C1] Every job is scheduled")
        print("  [C2] Start time trong [ready_date, deadline - duration]")
        print("  [C3] No overlap on the single machine")
        print("  [C4] Each job appears exactly once")
        print("  [C5] Precedence constraints are respected")
    else:
        print(f"\nINVALID - Found {len(violations)} violation(s):\n")
        for v in violations:
            print(f"  {v}")

    print("=" * 70)
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
