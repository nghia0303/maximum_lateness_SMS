import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENCODING_DIR = PROJECT_ROOT / "Encoding"
TEST_DIR = PROJECT_ROOT / "Test"
FILENAMES_DIR = PROJECT_ROOT / "Filenames"
DATA_2016_DIR = PROJECT_ROOT / "2016"
INS_DIR = DATA_2016_DIR / "Ins"
RESULTS_DIR = DATA_2016_DIR / "results"
SOLUTIONS_DIR = DATA_2016_DIR

DATASET_SIZES = [10, 20, 30, 40, 50]
INSTANCE_TYPES = ["S", "L"]
AVAILABLE_SOLVERS = [
    "directSAT",
    "proposedSAT",
    "cplex_mp",
    "gurobi",
    "cplex_cp",
    "cpsat",
]
DEFAULT_SOLVERS = ["directSAT", "proposedSAT"]


def configure_runtime_environment():
    encoding_path = str(ENCODING_DIR)
    if encoding_path not in sys.path:
        sys.path.insert(0, encoding_path)

    project_root = str(PROJECT_ROOT)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
