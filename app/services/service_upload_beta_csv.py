from __future__ import annotations

import contextlib
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import HTTPException, UploadFile

from app.celery_tasks.task_analyze_bvals_csv import task_analyze_bvals_csv
from app.schemas import CSVUploadResponse
from app.utils import file_utils as csvu


class UploadBetaValuesCSVService:
    def __init__(self, workdir: Path):
        self.workdir = Path(workdir)

    @contextlib.contextmanager
    def _tempdir(self):
        td = tempfile.TemporaryDirectory()
        try:
            yield Path(td.name)
        finally:
            td.cleanup()

    def _ensure_file_present_and_extension(self, file: UploadFile) -> None:
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        if not csvu.validate_csv_file(file):
            suffix = Path(file.filename).suffix if file.filename else "unknown"
            raise HTTPException(
                status_code=400,
                detail=f"Only CSV files are allowed. Got: {suffix}",
            )

    def _verify_or_compute_sha1(
        self, temp_file_path: Path, provided_id: Optional[str]
    ) -> str:
        calculated_hash = csvu.calculate_file_sha1(temp_file_path)
        if provided_id and provided_id != calculated_hash:
            raise HTTPException(
                status_code=400,
                detail=f"Provided id does not match calculated hash. Expected: {calculated_hash}, Got: {provided_id}",
            )
        return provided_id or calculated_hash

    def _ensure_not_already_uploaded(self, storage_dir: Path) -> bool:
        # Returns True if already uploaded
        return storage_dir.exists() and any(storage_dir.iterdir())

    def _validate_prognosis_column(self, temp_file_path: Path) -> None:
        try:
            # Read first 2 rows to get headers and first data row
            df = pd.read_csv(temp_file_path, nrows=2)
        except pd.errors.EmptyDataError:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        except pd.errors.ParserError as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Error validating CSV file: {str(e)}"
            )

        if len(df) < 1:
            raise HTTPException(
                status_code=400,
                detail="CSV file must contain at least 2 rows (sample headers and prognosis values row)",
            )

        # Check if first value of first row (index name) is "Prognosis"
        first_row_index = str(df.index[0]) if not df.empty else str(df.iloc[0, 0])

        # Try both index and first cell approaches
        if first_row_index != "Prognosis":
            # Check if first cell contains "Prognosis"
            first_cell_value = str(df.iloc[0, 0]) if len(df) > 0 else ""
            if first_cell_value != "Prognosis":
                raise HTTPException(
                    status_code=400,
                    detail=f"CSV validation failed: first row must start with 'Prognosis' (found: '{first_cell_value}'). Expected structure: columns are samples, first row contains prognosis values.",
                )

        # Check for prognosis values in the first row (excluding the "Prognosis" identifier)
        try:
            first_row = df.iloc[0]  # First row with prognosis values
            # Skip the first column if it contains "Prognosis", otherwise use all columns
            if str(first_row.iloc[0]) == "Prognosis":
                prognosis_values = first_row.iloc[
                    1:
                ].dropna()  # Skip "Prognosis" column
            else:
                prognosis_values = first_row.dropna()  # Use all values

            if len(prognosis_values) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="First row contains 'Prognosis' identifier but no prognosis values found",
                )
        except Exception:
            raise HTTPException(
                status_code=400, detail="Error reading prognosis values from first row"
            )

    async def handle_upload(
        self, file: UploadFile, provided_id: Optional[str]
    ) -> CSVUploadResponse:
        self._ensure_file_present_and_extension(file)

        with self._tempdir() as temp_dir:
            # Save upload to temp
            temp_file_path = await csvu.save_csv_file(file, temp_dir)

            # Prepare identifiers and storage paths
            sha1_hash = self._verify_or_compute_sha1(temp_file_path, provided_id)
            storage_dir = self.workdir / sha1_hash
            file_size = temp_file_path.stat().st_size

            # Fast path if already uploaded
            if self._ensure_not_already_uploaded(storage_dir):
                return CSVUploadResponse(
                    task_id="",
                    sha1_hash=sha1_hash,
                    message="File with this SHA1 hash already exists",
                    filename=file.filename,
                    file_size=file_size,
                )

            # Validate schema before persisting
            self._validate_prognosis_column(temp_file_path)

            # Persist and start processing
            storage_dir.mkdir(parents=True, exist_ok=True)
            final_file_path = storage_dir / "bval_data.csv"
            shutil.copy2(temp_file_path, final_file_path)

            task = task_analyze_bvals_csv.delay(
                file_path=str(final_file_path),
                sha1_hash=sha1_hash,
                storage_dir=str(storage_dir),
            )

            return CSVUploadResponse(
                task_id=task.id,
                sha1_hash=sha1_hash,
                message="CSV file uploaded successfully. Analysis started.",
                filename=file.filename,
                file_size=file_size,
            )
