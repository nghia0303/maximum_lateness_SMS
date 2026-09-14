# 2016 Benchmark Instances

This directory contains the selected `.GSP` instances used by the default
single-machine scheduling benchmark lane. The data are derived from the 2016
time-window and precedence benchmark family associated with Davari et al.

The selected public artifact contains 354 instances: 66 for 10 jobs and 72 for
each of 20, 30, 40, and 50 jobs. The authoritative selection is defined by the
text files in the repository root `Filenames/` directory.

The selected 10-job S instances named `10_10_005_100_25`,
`10_10_005_100_50`, and `10_10_005_100_75` use their `_2` replicas because the
corresponding `_1` files are corrupted. The 10-job L filelist retains its
original `_1` replicas.

For a size and type, the runner first uses `Filenames/{size}-{type}.txt` when
that file exists. It otherwise uses `Filenames/{size}.txt`. The corresponding
input path is:

```text
2016/Ins/wtrd_pred{size}/{type}/{filename}
```

Each `.GSP` file contains the job count, weights, processing durations, due
dates, release dates, hard deadlines, and precedence successor lists. The
objective uses durations and due dates to compute true `Lmax`; weights are
parsed for file compatibility but are not used in this objective.

Benchmark attribution and redistribution rights are separate from the MIT
license covering original code. Confirm the source benchmark's terms before
redistributing these files or publishing derived collections.
