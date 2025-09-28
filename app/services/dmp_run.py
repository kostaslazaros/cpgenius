from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd
from fastapi import HTTPException

from app.celery_tasks.dmp_tasks import dmp_selection_task
from app.schemas import DMPRequest, DMPResponse


class DmpRunService:
    def __init__(self, workdir: Path):
        self.workdir = Path(workdir)
        # Filenames containing these markers are considered result files, not originals
        self._algorithm_markers = ("stisdfs", "arapis", "dmp_result")

    def _storage_dir(self, sha1: str) -> Path:
        return self.workdir / sha1

    def _get_original_csv(self, storage_dir: Path) -> Path:
        if not storage_dir.exists():
            raise HTTPException(status_code=404, detail="File not found")

        csv_files = list(storage_dir.glob("*.csv"))
        if not csv_files:
            raise HTTPException(status_code=404, detail="CSV file not found")

        originals = [
            f
            for f in csv_files
            if not any(marker in f.name.lower() for marker in self._algorithm_markers)
        ]
        if not originals:
            raise HTTPException(
                status_code=404,
                detail="Original CSV file not found - only result files exist",
            )
        return originals[0]

    def _validate_thresholds(self, delta_beta: float, p_value: float) -> None:
        if not (0 <= delta_beta <= 1):
            raise HTTPException(
                status_code=400,
                detail=f"delta_beta must be between 0 and 1, got {delta_beta}",
            )
        if not (0 <= p_value <= 1):
            raise HTTPException(
                status_code=400,
                detail=f"p_value must be between 0 and 1, got {p_value}",
            )

    def _validate_groups(self, csv_file: Path, selected: List[str]) -> Tuple[str, str]:
        if len(selected) != 2:
            raise HTTPException(
                status_code=400,
                detail=f"DMP analysis requires exactly 2 prognosis groups, got {len(selected)}",
            )

        # Ensure selected groups exist in CSV - read from first row (transposed structure)
        try:
            # Read first row to get prognosis values
            df = pd.read_csv(csv_file, nrows=1)

            if len(df) < 1:
                raise HTTPException(
                    status_code=400,
                    detail="CSV file must contain at least 1 row with prognosis values",
                )

            # Get prognosis values from first row
            first_row = df.iloc[0]  # First row with prognosis values

            # Check if first cell is "Prognosis" and handle accordingly
            if str(first_row.iloc[0]) == "Prognosis":
                # Skip the "Prognosis" identifier column
                prognosis_values = first_row.iloc[1:].dropna()
            else:
                # Use all values in first row as prognosis values
                prognosis_values = first_row.dropna()

            if len(prognosis_values) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No prognosis values found in first row of transposed CSV",
                )

            # Extract unique prognosis values
            uniques = set(str(v) for v in prognosis_values.unique().tolist())

        except pd.errors.EmptyDataError:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        except pd.errors.ParserError as e:
            raise HTTPException(
                status_code=400, detail=f"Error parsing CSV file: {str(e)}"
            )

        missing = [g for g in selected if str(g) not in uniques]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Selected prognosis values not found in file: {missing}",
            )

        # Return normalized values as strings
        return str(selected[0]), str(selected[1])

    async def start(self, request: DMPRequest) -> DMPResponse:
        storage_dir = self._storage_dir(request.sha1_hash)
        csv_file = self._get_original_csv(storage_dir)

        self._validate_thresholds(request.delta_beta, request.p_value)
        cond1, cond2 = self._validate_groups(
            csv_file, request.selected_prognosis_values
        )

        try:
            task = dmp_selection_task.delay(
                storage_dir=str(storage_dir),
                condition_1=cond1,
                condition_2=cond2,
                delta_beta=request.delta_beta,
                p_value=request.p_value,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error starting DMP analysis: {str(e)}"
            )

        return DMPResponse(
            task_id=task.id,
            sha1_hash=request.sha1_hash,
            selected_values=[cond1, cond2],
            message=(
                f"DMP analysis started for groups: {cond1}, {cond2} "
                f"(delta_beta={request.delta_beta}, p_value={request.p_value})"
            ),
        )
