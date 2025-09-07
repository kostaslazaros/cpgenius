import pandas as pd
from fastapi import HTTPException

from app.config import cnf
from app.schemas import (
    PrognosisValuesResponse,
)

PROGNOSIS_COLUMN_NAME = cnf.prognosis_column_name  # "Prognosis" by default


def get_prognosis_values_from_csv(sha1_hash: str):
    storage_dir = cnf.dmp_workdir / sha1_hash

    if not storage_dir.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # Find the ORIGINAL CSV file (not result files)
        csv_files = list(storage_dir.glob("*.csv"))
        if not csv_files:
            raise HTTPException(
                status_code=404, detail="CSV file not found in storage directory"
            )

        csv_file = csv_files[0]
        # Read CSV and extract unique Prognosis values
        try:
            df = pd.read_csv(csv_file)

            # STRICT CHECK: Prognosis column must exist
            if PROGNOSIS_COLUMN_NAME not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"CSV file must contain a '{PROGNOSIS_COLUMN_NAME}' column. Found columns: {list(df.columns)}",
                )

            # Get unique values from Prognosis column (excluding NaN)
            unique_values = df[PROGNOSIS_COLUMN_NAME].dropna().unique().tolist()
            unique_values = [str(val) for val in unique_values]  # Convert to strings
            unique_values.sort()  # Sort alphabetically

            return PrognosisValuesResponse(
                sha1_hash=sha1_hash,
                filename=csv_file.name,
                unique_values=unique_values,
                total_rows=len(df),
                total_columns=len(df.columns),
                prognosis_column_found=True,
                message=f"Found {len(unique_values)} unique prognosis values",
            )

        except pd.errors.EmptyDataError:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        except pd.errors.ParserError as e:
            raise HTTPException(
                status_code=400, detail=f"Error parsing CSV file: {str(e)}"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading CSV file: {str(e)}")
