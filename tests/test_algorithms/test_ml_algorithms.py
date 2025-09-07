from pathlib import Path

import pytest

# from app.algorithms.selector import ALGORITHMS
from app.services.get_algorithms import ALGORITHMS
from app.utils.algorithm_utils import fs_wrapper

PATH = Path(__file__).parent.parent / "test_data"
DEMO_CSV = PATH / "bval_data.csv"


@pytest.mark.parametrize("algorithm", ALGORITHMS.values())
def test_algorithms(algorithm):
    results = fs_wrapper(algorithm=algorithm, csv_path=DEMO_CSV)
    print(results["feature_ranking"].head())
    assert results["feature_ranking"].shape[1] == 2
