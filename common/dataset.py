from pathlib import Path
from typing import Dict, List, Tuple


DatasetTuple = Tuple[int, Dict[int, int], Dict[int, int], Dict[int, int], Dict[int, int], Dict[int, List[int]]]


def read_dataset(path) -> DatasetTuple:
    dataset_path = Path(path)
    with open(dataset_path, "r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]

    index = 0
    assert lines[index].startswith("n")
    index += 1
    job_count = int(lines[index])
    index += 1

    def read_values(label: str) -> Dict[int, int]:
        nonlocal index
        assert label in lines[index]
        index += 1
        values = list(map(int, lines[index].split()))
        index += 1
        return {job + 1: values[job] for job in range(job_count)}

    read_values("weight")
    durations = read_values("duration")
    due_dates = read_values("due date")
    ready_dates = read_values("ready date")
    deadlines = read_values("deadline")

    assert "precedence relations" in lines[index]
    index += 1

    successors = {job: [] for job in range(1, job_count + 1)}
    for job in range(1, job_count + 1):
        parts = list(map(int, lines[index].split()))
        index += 1
        successors[job] = [successor for successor in parts[1:] if successor <= job_count]

    return job_count, durations, ready_dates, due_dates, deadlines, successors
