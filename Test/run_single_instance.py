import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from runner_common import AVAILABLE_SOLVERS, parse_solution_file, run_single_instance


SUBPROCESS_GRACE = 20


def main():
    if len(sys.argv) == 6 and sys.argv[1] == "--single":
        _, _, dataset_file, solution_file, solver, timeout = sys.argv
        run_single_instance(Path(dataset_file), Path(solution_file), solver, int(timeout), verbose=True)
        return

    parser = argparse.ArgumentParser(
        description="Run one instance without writing persistent solution or Excel outputs."
    )
    parser.add_argument("instance", help="Path to the .GSP instance file")
    parser.add_argument(
        "--solver",
        required=True,
        choices=AVAILABLE_SOLVERS,
        help="Solver to run",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Per-instance timeout in seconds (default: 300)",
    )

    args = parser.parse_args()
    instance_path = Path(args.instance).resolve()

    if not instance_path.exists():
        raise FileNotFoundError(f"Instance file not found: {instance_path}")

    with tempfile.TemporaryDirectory(prefix="smsp_run_") as temp_dir:
        temp_solution = Path(temp_dir) / f"{instance_path.name}.txt"
        script_path = Path(__file__).resolve()

        started_at = time.time()
        status = "FINISHED"
        process = subprocess.Popen(
            [
                sys.executable,
                str(script_path),
                "--single",
                str(instance_path),
                str(temp_solution),
                args.solver,
                str(args.timeout),
            ],
        )
        try:
            process.wait(timeout=args.timeout)
            elapsed = time.time() - started_at
        except subprocess.TimeoutExpired:
            status = "TIMEOUT"
            elapsed = float(args.timeout)
            try:
                process.wait(timeout=SUBPROCESS_GRACE)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        time.sleep(0.1)
        lmax, status, gap, sat_stats = parse_solution_file(temp_solution, args.solver, status)

        if status == "TIMEOUT":
            elapsed = float(args.timeout)

    print("=" * 70)
    print("Single Instance Run")
    print("=" * 70)
    print(f"Instance : {instance_path}")
    print(f"Solver   : {args.solver}")
    print(f"Timeout  : {args.timeout}s")
    print(f"Status   : {status}")
    print(f"Lmax     : {lmax}")
    if gap is not None:
        print(f"Gap      : {gap:.2f}%")
    print(f"Time     : {elapsed:.2f}s")
    if sat_stats:
        print(f"Conflicts    : {sat_stats.get('conflicts', 'N/A')}")
        print(f"Decisions    : {sat_stats.get('decisions', 'N/A')}")
        print(f"Propagations : {sat_stats.get('propagations', 'N/A')}")
        print(f"Restarts     : {sat_stats.get('restarts', 'N/A')}")
    print("Output   : no persistent solution or Excel file written")
    print("=" * 70)


if __name__ == "__main__":
    main()
