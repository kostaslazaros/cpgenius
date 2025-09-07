from pathlib import Path

from app.utils.file_utils import csv2first_n_rows

current_dir = Path(__file__).parent.resolve()


def test_csv2first_n_rows():
    input_file = current_dir / "test_data" / "ranked_features_lasso_logistic.csv"
    output_file = (
        current_dir / "test_data" / "ranked_features_lasso_logistic_first_10.csv"
    )
    result_file = csv2first_n_rows(str(input_file.resolve()), 10)
    assert Path(result_file) == output_file
    assert output_file.exists()

    file_to_delete = Path(result_file)
    if file_to_delete.exists():
        file_to_delete.unlink()
