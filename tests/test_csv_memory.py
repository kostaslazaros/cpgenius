import tempfile
from io import StringIO
from pathlib import Path

import pandas as pd

from app.utils.file_utils import csv2first_n_rows_memory


def test_csv2first_n_rows_memory():
    """Test in-memory CSV processing without creating temporary files."""
    # Create test data
    test_data = {
        "col1": [1, 2, 3, 4, 5],
        "col2": ["a", "b", "c", "d", "e"],
        "col3": [1.1, 2.2, 3.3, 4.4, 5.5],
    }
    df = pd.DataFrame(test_data)

    # Create temporary CSV file for testing
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False
    ) as temp_file:
        df.to_csv(temp_file.name, index=False)
        temp_csv_path = temp_file.name

    try:
        # Test reading first 3 rows
        result_io = csv2first_n_rows_memory(temp_csv_path, 3)

        # Verify result is StringIO object
        assert isinstance(result_io, StringIO)

        # Get CSV content
        csv_content = result_io.getvalue()

        # Parse the result back to verify correctness
        result_df = pd.read_csv(StringIO(csv_content))

        # Should have only first 3 rows
        assert len(result_df) == 3
        assert list(result_df.columns) == ["col1", "col2", "col3"]
        assert result_df["col1"].tolist() == [1, 2, 3]
        assert result_df["col2"].tolist() == ["a", "b", "c"]

        # Test with more rows than available
        result_io_large = csv2first_n_rows_memory(temp_csv_path, 10)
        csv_content_large = result_io_large.getvalue()
        result_df_large = pd.read_csv(StringIO(csv_content_large))

        # Should have all 5 rows (limited by available data)
        assert len(result_df_large) == 5

    finally:
        # Clean up temporary file
        Path(temp_csv_path).unlink()


def test_csv2first_n_rows_memory_empty_file():
    """Test behavior with empty CSV file."""
    # Create empty CSV with headers only
    df_empty = pd.DataFrame(columns=["col1", "col2"])

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False
    ) as temp_file:
        df_empty.to_csv(temp_file.name, index=False)
        temp_csv_path = temp_file.name

    try:
        result_io = csv2first_n_rows_memory(temp_csv_path, 5)
        csv_content = result_io.getvalue()
        result_df = pd.read_csv(StringIO(csv_content))

        # Should have headers but no data rows
        assert len(result_df) == 0
        assert list(result_df.columns) == ["col1", "col2"]

    finally:
        Path(temp_csv_path).unlink()
