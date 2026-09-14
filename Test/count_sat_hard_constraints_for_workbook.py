"""
Count hard-constraint SAT size metrics for the authoritative filename lists.

This script uses the authoritative filename lists and records only base CNF
size (variables and clauses) for:
- `directSAT`
- `proposedSAT` (displayed as `PROPOSED SAT`)

Incremental optimization clauses are intentionally excluded.
"""

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
ENCODING_DIR = PROJECT_ROOT / "Encoding"
if str(ENCODING_DIR) not in sys.path:
    sys.path.insert(0, str(ENCODING_DIR))

from common.dataset import read_dataset
from common.project_paths import DATASET_SIZES, FILENAMES_DIR, INS_DIR, INSTANCE_TYPES, RESULTS_DIR
from common.schedule_utils import window_tightening
from directSAT import count_hard_cnf as count_directsat_hard_cnf
from proposedSAT import count_hard_cnf as count_proposed_hard_cnf


OUTPUT_WORKBOOK = RESULTS_DIR / "sat_hard_constraint_stats.xlsx"


def read_filename_instances():
    rows = []
    for size in DATASET_SIZES:
        for instance_type in INSTANCE_TYPES:
            type_specific = FILENAMES_DIR / f"{size}-{instance_type}.txt"
            filelist = type_specific if type_specific.exists() else FILENAMES_DIR / f"{size}.txt"
            if not filelist.exists():
                raise FileNotFoundError(f"Filename list not found: {filelist}")
            for line in filelist.read_text(encoding="utf-8").splitlines():
                filename = line.strip()
                if filename:
                    rows.append({"n": size, "type": instance_type, "filename": filename})
    return rows


def count_instance_rows(instance_rows):
    stats_rows = []
    current_size = None

    for index, instance in enumerate(instance_rows, start=1):
        size = instance["n"]
        instance_type = instance["type"]
        filename = instance["filename"]

        if size != current_size:
            current_size = size
            print(f"Counting SAT hard constraints for {size}-job rows...")

        instance_file = INS_DIR / f"wtrd_pred{size}" / instance_type / filename
        n, durations, ready_dates, due_dates, deadlines, successors = read_dataset(instance_file)
        tightened_ready, tightened_deadlines = window_tightening(n, ready_dates, durations, deadlines, successors)

        directsat_vars, directsat_clauses = count_directsat_hard_cnf(
            n,
            durations,
            tightened_ready,
            tightened_deadlines,
            successors,
        )
        proposed_vars, proposed_clauses = count_proposed_hard_cnf(
            n,
            durations,
            tightened_ready,
            tightened_deadlines,
            successors,
        )

        for solver_name, var_count, clause_count in (
            ("directSAT", directsat_vars, directsat_clauses),
            ("proposedSAT", proposed_vars, proposed_clauses),
        ):
            stats_rows.append(
                {
                    "solver": solver_name,
                    "dataset": f"{size}-{instance_type}",
                    "filename": filename,
                    "n": n,
                    "type": instance_type,
                    "vars": var_count,
                    "clauses": clause_count,
                }
            )

        if index % 25 == 0 or index == len(instance_rows):
            print(f"  processed {index}/{len(instance_rows)} workbook instances")

    return stats_rows


def save_stats_workbook(output_path: Path, rows):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name="stats", index=False)


def main():
    instance_rows = read_filename_instances()
    stats_rows = count_instance_rows(instance_rows)
    save_stats_workbook(OUTPUT_WORKBOOK, stats_rows)
    print(f"Created SAT hard-constraint stats workbook: {OUTPUT_WORKBOOK}")


if __name__ == "__main__":
    main()
