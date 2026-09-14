"""
run_batch_from_filelist.py

Run batch experiments from filename lists in `Filenames/`.

Mapping:
  - `Filenames/10.txt` -> `2016/Ins/wtrd_pred10/{S|L}/<filename>`
  - `Filenames/20.txt` -> `2016/Ins/wtrd_pred20/{S|L}/<filename>`

Outputs:
  - Solutions: `2016/solutions_{solver}/{n}-{type}/`
  - Excel: `2016/results/results_{solver}.xlsx` with sheets `10-S`, `10-L`, ..., `50-L`
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

from runner_common import (
    AVAILABLE_SOLVERS,
    DATASET_SIZES,
    DEFAULT_SOLVERS,
    INSTANCE_TYPES,
    RESULTS_DIR,
    SOLUTIONS_DIR,
    build_sheet_names,
    dataset_sheet,
    instance_path,
    load_filename_list,
    load_results_from_excel,
    parse_solution_file,
    run_single_instance,
    save_results_to_excel,
)


TIMEOUT = 300
SUBPROCESS_GRACE = 20


def main(solvers=None, instance_types=None):
    selected_solvers = list(solvers or DEFAULT_SOLVERS)
    selected_types = list(instance_types or INSTANCE_TYPES)
    sheets = build_sheet_names(selected_types)

    print("=" * 70)
    print("Batch Runner - Multiple Solvers")
    print("=" * 70)
    print(f"Sizes    : {', '.join(str(size) for size in DATASET_SIZES)}")
    print(f"Types    : {', '.join(selected_types)}")
    print(f"Solvers  : {', '.join(selected_solvers)}")
    print(f"Timeout  : {TIMEOUT}s per instance")
    print("=" * 70)

    script_path = Path(__file__).resolve()

    for solver in selected_solvers:
        print(f"\n{'#' * 70}")
        print(f"# SOLVER: {solver.upper()}")
        print(f"{'#' * 70}\n")

        excel_file = RESULTS_DIR / f"results_{solver}.xlsx"
        all_results = {sheet: [] for sheet in sheets}
        if excel_file.exists():
            print(f"    [RESUME] Loading existing results from {excel_file.name}")
            try:
                all_results = load_results_from_excel(excel_file, sheets)
                for sheet in sheets:
                    if all_results[sheet]:
                        print(f"      - Sheet '{sheet}': {len(all_results[sheet])} records")
            except Exception as exc:
                print(f"    [WARNING] Could not read Excel file: {exc}")

        for size in DATASET_SIZES:
            for instance_type in selected_types:
                instances = load_filename_list(size, instance_type)
                if instances is None:
                    print(f"[SKIP] size={size}, type={instance_type} - file list not found")
                    continue

                sheet = dataset_sheet(size, instance_type)
                print(f"\n>>> Dataset: {sheet} - {len(instances)} instances")

                solution_dir = SOLUTIONS_DIR / f"solutions_{solver}" / sheet
                completed = {row["filename"] for row in all_results[sheet]} if all_results[sheet] else set()
                if completed:
                    print(f"    [RESUME] Found {len(completed)} completed instances")

                for index, filename in enumerate(instances, 1):
                    dataset_file = instance_path(size, instance_type, filename)
                    solution_file = solution_dir / f"{filename}.txt"

                    if filename in completed:
                        print(f"  [{index}/{len(instances)}] {filename} - SKIP (already completed)")
                        continue

                    if not dataset_file.exists():
                        print(f"  [{index}/{len(instances)}] {filename} - FILE NOT FOUND")
                        all_results[sheet].append({
                            "solver": solver,
                            "dataset": sheet,
                            "filename": filename,
                            "n": size,
                            "type": instance_type,
                            "Lmax": "-",
                            "status": "FILE_NOT_FOUND",
                            "time_s": 0,
                            "gap_%": None,
                        })
                        save_results_to_excel(excel_file, all_results, sheets)
                        continue

                    print(f"  [{index}/{len(instances)}] {filename} ... ", end="", flush=True)

                    process = subprocess.Popen(
                        [
                            sys.executable,
                            str(script_path),
                            "--single",
                            str(dataset_file),
                            str(solution_file),
                            solver,
                            str(TIMEOUT),
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

                    started_at = time.time()
                    status = "FINISHED"
                    try:
                        process.wait(timeout=TIMEOUT)
                        elapsed = time.time() - started_at
                    except subprocess.TimeoutExpired:
                        status = "TIMEOUT"
                        elapsed = float(TIMEOUT)
                        try:
                            process.wait(timeout=SUBPROCESS_GRACE)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()

                    time.sleep(0.1)
                    parsed = parse_solution_file(solution_file, solver, status)
                    if len(parsed) == 4:
                        lmax, status, gap, _ = parsed
                    else:
                        lmax, status, gap = parsed

                    if status == "TIMEOUT":
                        elapsed = float(TIMEOUT)

                    gap_text = f"gap={gap:.2f}% | " if gap is not None else ""
                    print(f"{status} | Lmax={lmax} | {gap_text}{elapsed:.2f}s")

                    all_results[sheet].append({
                        "solver": solver,
                        "dataset": sheet,
                        "filename": filename,
                        "n": size,
                        "type": instance_type,
                        "Lmax": lmax,
                        "status": status,
                        "time_s": round(elapsed, 2),
                        "gap_%": round(gap, 2) if gap is not None else None,
                    })
                    save_results_to_excel(excel_file, all_results, sheets)

        print(f"\n    -> Results saved: {excel_file}")
        total_records = sum(len(all_results[sheet]) for sheet in sheets)
        print(f"       Total records: {total_records}")

    print("\n" + "=" * 70)
    print("All done!")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "--single":
        _, _, dataset_file, solution_file, solver, timeout = sys.argv
        run_single_instance(Path(dataset_file), Path(solution_file), solver, int(timeout))
    else:
        parser = argparse.ArgumentParser(
            description="Run batch experiments with multiple solvers",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python Test/run_batch_from_filelist.py
  python Test/run_batch_from_filelist.py --types S
  python Test/run_batch_from_filelist.py --types S L --solvers directSAT proposedSAT
  python Test/run_batch_from_filelist.py --solvers cplex_mp gurobi cplex_cp cpsat
            """,
        )

        parser.add_argument(
            "--solvers",
            nargs="+",
            choices=AVAILABLE_SOLVERS,
            default=None,
            help=f"Solvers to run (default: {', '.join(DEFAULT_SOLVERS)})",
        )
        parser.add_argument(
            "--types",
            nargs="+",
            choices=INSTANCE_TYPES,
            default=None,
            help="Instance types to run (default: S L)",
        )

        args = parser.parse_args()
        main(solvers=args.solvers, instance_types=args.types)
