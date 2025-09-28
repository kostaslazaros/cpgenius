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
        # Read CSV and extract unique Prognosis values from first row
        try:
            # Read first row to get prognosis values (transposed structure)
            df = pd.read_csv(csv_file, nrows=1)

            if len(df) < 1:
                raise HTTPException(
                    status_code=400,
                    detail="CSV file must contain at least 1 row with prognosis values",
                )

            # Get the first row which should contain prognosis values
            first_row = df.iloc[0]

            # Check if first cell is "Prognosis" and skip it, or use all values
            if str(first_row.iloc[0]) == PROGNOSIS_COLUMN_NAME:
                # Skip the "Prognosis" identifier column
                prognosis_values = first_row.iloc[1:].dropna()
            else:
                # Use all values in first row as prognosis values
                prognosis_values = first_row.dropna()

            if len(prognosis_values) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="No prognosis values found in first row. Expected transposed structure with samples as columns.",
                )

            # Get unique values and process them
            unique_values = prognosis_values.unique().tolist()
            unique_values = [str(val) for val in unique_values]  # Convert to strings
            unique_values = list(set(unique_values))  # Remove duplicates
            unique_values.sort()  # Sort alphabetically

            # Read full file to get total dimensions for response
            df_full = pd.read_csv(csv_file)

            return PrognosisValuesResponse(
                sha1_hash=sha1_hash,
                filename=csv_file.name,
                unique_values=unique_values,
                total_rows=len(df_full),  # Number of CpG sites
                total_columns=len(df_full.columns),  # Number of samples
                prognosis_column_found=True,
                message=f"Found {len(unique_values)} unique prognosis values from transposed structure (columns=samples, rows=CpG sites)",
            )

        except pd.errors.EmptyDataError:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        except pd.errors.ParserError as e:
            raise HTTPException(
                status_code=400, detail=f"Error parsing CSV file: {str(e)}"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading CSV file: {str(e)}")
