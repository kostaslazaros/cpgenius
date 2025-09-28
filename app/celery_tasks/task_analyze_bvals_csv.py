import json
import time
from pathlib import Path

import pandas as pd

from app.config import cnf
from app.utils.json_utils import serialize_for_json

from ..cpg2gene.cpg_gene_mapping import (
    guess_illumina_array_type_pd,
)

# from ..algorithms.selector import ALGORITHMS
from .celery import app

PROGNOSIS_COLUMN = cnf.prognosis_column_name
OUT = cnf.fs_outdir_name


@app.task(bind=True)
def task_analyze_bvals_csv(self, file_path: str, sha1_hash: str, storage_dir: str):
    """
    Analyze the uploaded CSV file and extract prognosis information.
    This is a quick task that validates the file and extracts metadata.
    """
    try:
        self.update_state(
            state="PROCESSING", meta={"status": "Starting CSV analysis", "progress": 0}
        )

        file_path_obj = Path(file_path)

        # Basic file validation
        if not file_path_obj.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        # Read CSV file
        try:
            df = pd.read_csv(file_path_obj)
        except Exception as e:
            raise ValueError(f"Error reading CSV file: {str(e)}")

        self.update_state(
            state="PROCESSING",
            meta={"status": "Analyzing CSV structure", "progress": 30},
        )

        # STRICT VALIDATION: First row must contain prognosis values (transposed structure)
        if len(df) < 1:
            raise ValueError(
                "CSV file must contain at least 1 row with prognosis values (transposed structure: columns=samples, rows=CpG sites)"
            )

        # Get first row which should contain prognosis values
        first_row = df.iloc[0]  # First row

        # Handle CSV with index column (like "Unnamed: 0") - check if first cell is "Prognosis"
        first_cell_value = str(first_row.iloc[0])

        if first_cell_value == PROGNOSIS_COLUMN:
            # First cell is "Prognosis" identifier in index column, actual values start from column 1
            prognosis_values = first_row.iloc[1:].dropna()  # Skip index column
        else:
            # Check if this might be a CSV with row labels column
            # Look for "Prognosis" in first column (index/row labels)
            if hasattr(df, "index") and len(df.index) > 0:
                first_index_value = str(df.index[0])
                if first_index_value == PROGNOSIS_COLUMN:
                    # Row index contains "Prognosis", use all column values from first row
                    prognosis_values = first_row.dropna()
                else:
                    # Neither first cell nor first index is "Prognosis", this might not be the expected format
                    prognosis_values = first_row.dropna()  # Try using all values anyway
            else:
                # First cell is already a prognosis value, use all values
                prognosis_values = first_row.dropna()

        if len(prognosis_values) == 0:
            raise ValueError(
                "No prognosis values found in first row of transposed CSV structure"
            )

        self.update_state(
            state="PROCESSING",
            meta={"status": "Guessing Illumina array type", "progress": 30},
        )

        illumina_types = guess_illumina_array_type_pd(
            df.index[1:] if len(df) > 1 else pd.Index([])
        )

        result = {
            "sha1_hash": sha1_hash,
            "filename": file_path_obj.name,
            "file_size": int(file_path_obj.stat().st_size),
            "rows": int(len(df)),  # Number of CpG sites (plus prognosis row)
            "columns": int(len(df.columns)),  # Number of samples
            "prognosis_column": "First row (transposed structure)",
            "analysis_time": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "detected_illumina_array_types": illumina_types,
            "structure_type": "transposed",  # Document the structure type
        }

        # Get prognosis statistics from first data row values (we know they exist)
        unique_values = prognosis_values.unique().tolist()
        value_counts = prognosis_values.value_counts().to_dict()

        result.update(
            {
                "prognosis_unique_values": [str(val) for val in sorted(unique_values)],
                "prognosis_value_counts": int(len(unique_values)),
                "prognosis_null_count": 0,  # We already filtered out NaN values
                "prognosis_distribution": {
                    str(k): int(v) for k, v in value_counts.items()
                },
            }
        )

        self.update_state(
            state="PROCESSING",
            meta={"status": "Saving analysis results", "progress": 80},
        )

        # Save analysis results to JSON file normally analysis42.json
        analysis_file = Path(storage_dir) / cnf.metadata_file
        with open(analysis_file, "w") as f:
            # Use serialize_for_json to ensure all data types are JSON-compatible
            json.dump(serialize_for_json(result), f, indent=2, default=str)

        self.update_state(
            state="SUCCESS",
            meta={
                "status": "CSV analysis completed",
                "progress": 100,
                "result": serialize_for_json(result),
            },
        )

        return serialize_for_json(result)

    except FileNotFoundError as exc:
        # Handle file not found specifically
        error_msg = f"CSV file not found: {str(exc)}"
        self.update_state(
            state="FAILURE",
            meta={
                "status": error_msg,
                "error": error_msg,
                "exc_type": "FileNotFoundError",
                "exc_message": error_msg,
            },
        )
        raise FileNotFoundError(error_msg)

    except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        # Handle pandas-specific CSV errors
        error_msg = f"CSV parsing error: {str(exc)}"
        self.update_state(
            state="FAILURE",
            meta={
                "status": error_msg,
                "error": error_msg,
                "exc_type": type(exc).__name__,
                "exc_message": error_msg,
            },
        )
        raise ValueError(error_msg)

    except ValueError as exc:
        # Handle validation errors (like missing Prognosis column)
        error_msg = f"CSV validation error: {str(exc)}"
        self.update_state(
            state="FAILURE",
            meta={
                "status": error_msg,
                "error": error_msg,
                "exc_type": "ValueError",
                "exc_message": error_msg,
            },
        )
        raise ValueError(error_msg)

    except Exception as exc:
        # Catch-all for any other unexpected exceptions
        error_msg = str(exc)
        exc_type = type(exc).__name__

        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Unexpected error analyzing CSV: {error_msg}",
                "error": error_msg,
                "exc_type": exc_type,
                "exc_message": error_msg,
            },
        )

        # Don't convert exception types, just re-raise the original
        # Let Celery handle the serialization
        raise
