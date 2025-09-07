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

        # STRICT VALIDATION: Prognosis column is required
        if "Prognosis" not in df.columns:
            raise ValueError(
                f"CSV file must contain a 'Prognosis' column. Found columns: {list(df.columns)}"
            )

        # Check if Prognosis column has any non-null values
        prognosis_series = df[PROGNOSIS_COLUMN].dropna()
        if len(prognosis_series) == 0:
            raise ValueError(
                f"{PROGNOSIS_COLUMN} column exists but contains no valid values (all null/empty)"
            )

        self.update_state(
            state="PROCESSING",
            meta={"status": "Guessing Illumina array type", "progress": 30},
        )

        illumina_types = guess_illumina_array_type_pd(df.columns.drop("Prognosis"))

        result = {
            "sha1_hash": sha1_hash,
            "filename": file_path_obj.name,
            "file_size": int(file_path_obj.stat().st_size),
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "prognosis_column": PROGNOSIS_COLUMN,
            "analysis_time": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "detected_illumina_array_types": illumina_types,
        }

        # Get prognosis column statistics (we know it exists and has values)
        unique_values = prognosis_series.unique().tolist()

        result.update(
            {
                "prognosis_unique_values": [str(val) for val in sorted(unique_values)],
                "prognosis_value_counts": int(len(unique_values)),
                "prognosis_null_count": int(df[PROGNOSIS_COLUMN].isna().sum()),
                "prognosis_distribution": {
                    str(k): int(v)
                    for k, v in df[PROGNOSIS_COLUMN].value_counts().to_dict().items()
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
