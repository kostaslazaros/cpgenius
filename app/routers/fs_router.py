# Feature Selection Router
# Handles uploading CSV files, running algorithms, and managing results
import shutil

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.celery_tasks.fs_tasks import (
    process_prognosis_algorithm,
)
from app.config import cnf
from app.schemas import (
    Algorithm,
    AlgorithmRequest,
    AlgorithmResponse,
    CSVUploadResponse,
    PrognosisValuesResponse,
    TaskStatus,
)
from app.services.get_algorithms import get_algorithms
from app.services.service_upload_beta_csv import UploadBetaValuesCSVService
from app.utils.get_metadata import get_metadata

router = APIRouter(prefix=cnf.prefix_fs, tags=["Feature Selection"])

# ALLOWED_EXTENSIONS = {".csv"}
upload_service = UploadBetaValuesCSVService(cnf.fs_workdir)

OUT = cnf.fs_outdir_name


@router.post("/upload", response_model=CSVUploadResponse)
async def upload_csv_file(
    file: UploadFile = File(..., description="Upload a CSV file with Prognosis column"),
    id: str = Form(None),  # Optional SHA1 hash from frontend
):
    return await upload_service.handle_upload(file, id)


@router.get("/exists/{sha1_hash}")
async def check_file_exists(sha1_hash: str):
    """Check if a file with the given SHA1 hash exists."""
    storage_dir = cnf.fs_workdir / sha1_hash
    exists = storage_dir.exists() and any(storage_dir.iterdir())
    return {"sha1_hash": sha1_hash, "exists": exists}


@router.get("/algorithms")
async def get_available_algorithms():
    """Get list of available feature selection algorithms."""
    return get_algorithms()


@router.get("/prognosis-values/{sha1_hash}", response_model=PrognosisValuesResponse)
async def get_prognosis_values(sha1_hash: str):
    """Get unique values from the Prognosis column of the uploaded CSV file."""
    storage_dir = cnf.fs_workdir / sha1_hash

    if not storage_dir.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # Find the ORIGINAL CSV file (not result files)
        csv_files = list(storage_dir.glob("*.csv"))
        if not csv_files:
            raise HTTPException(
                status_code=404, detail="CSV file not found in storage directory"
            )

        # Filter out result files - original file shouldn't have algorithm names in it
        algorithm_names = [alg.value for alg in Algorithm]
        original_csv_files = [
            f
            for f in csv_files
            if not any(alg_name in f.name.lower() for alg_name in algorithm_names)
        ]

        if not original_csv_files:
            raise HTTPException(
                status_code=404,
                detail="Original CSV file not found - only result files exist",
            )

        # Use the first original CSV file (should be only one)
        csv_file = original_csv_files[0]

        # Read CSV and extract unique Prognosis values
        try:
            df = pd.read_csv(csv_file)

            # STRICT CHECK: Prognosis column must exist
            if "Prognosis" not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"CSV file must contain a 'Prognosis' column. Found columns: {list(df.columns)}",
                )

            # Get unique values from Prognosis column (excluding NaN)
            unique_values = df["Prognosis"].dropna().unique().tolist()
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


@router.post("/run-algorithm", response_model=AlgorithmResponse)
async def run_algorithm(request: AlgorithmRequest):
    """
    Run a machine learning algorithm on selected prognosis values.
    """
    storage_dir = cnf.fs_workdir / request.sha1_hash

    if not storage_dir.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Find the ORIGINAL CSV file (not result files)
    csv_files = list(storage_dir.glob("*.csv"))
    if not csv_files:
        raise HTTPException(status_code=404, detail="CSV file not found")

    # Filter out result files - original file shouldn't have algorithm names in it
    algorithm_names = [alg.value for alg in Algorithm]
    original_csv_files = [
        f
        for f in csv_files
        if not any(alg_name in f.name.lower() for alg_name in algorithm_names)
    ]

    if not original_csv_files:
        raise HTTPException(
            status_code=404,
            detail="Original CSV file not found - only result files exist",
        )

    # Use the first original CSV file (should be only one)
    csv_file = original_csv_files[0]

    try:
        # Start Celery task for algorithm processing
        task = process_prognosis_algorithm.delay(
            file_path=str(csv_file),
            sha1_hash=request.sha1_hash,
            storage_dir=str(storage_dir),
            selected_prognosis=request.selected_prognosis_values,
            algorithm=request.algorithm.value,
        )

        return AlgorithmResponse(
            task_id=task.id,
            sha1_hash=request.sha1_hash,
            algorithm=request.algorithm.value,
            selected_values=request.selected_prognosis_values,
            message=f"Algorithm {request.algorithm.value} started for {len(request.selected_prognosis_values)} prognosis values",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error starting algorithm: {str(e)}"
        )


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get the status of a prognosis analysis task."""
    from app.celery_tasks.celery import app as celery_app

    try:
        task_result = celery_app.AsyncResult(task_id)

        status_response = TaskStatus(
            task_id=task_id, status=task_result.status, result=task_result.info
        )

        if task_result.ready():
            if task_result.successful():
                status_response.result = task_result.result
            else:
                status_response.error = str(task_result.info)

        return status_response

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking task status: {str(e)}"
        )


@router.get("/list")
async def list_uploaded_files():
    """List all uploaded CSV files by SHA1 hash."""
    if not cnf.fs_workdir.exists():
        return {"files": []}

    files = []
    for dir_path in cnf.fs_workdir.iterdir():
        if dir_path.is_dir():
            csv_files = list(dir_path.glob("*.csv"))
            if csv_files:
                csv_file = csv_files[0]
                files.append(
                    {
                        "sha1_hash": dir_path.name,
                        "filename": csv_file.name,
                        "file_size": csv_file.stat().st_size,
                        "created_time": dir_path.stat().st_ctime,
                    }
                )

    return {"files": files}


@router.get("/results/{sha1_hash}")
async def list_results(sha1_hash: str):
    """List all algorithm result files for a given SHA1 hash."""
    storage_dir = cnf.fs_workdir / sha1_hash / OUT

    if not storage_dir.exists():
        raise HTTPException(status_code=404, detail="Directory not found")

    # Look for result files (CSV files that are not the original)
    all_files = list(storage_dir.glob("*.csv"))

    # The original file should be the one without algorithm name in filename

    result_files = [
        f for f in all_files if any(alg.value in f.name.lower() for alg in Algorithm)
    ]

    results = []
    for result_file in result_files:
        results.append(
            {
                "filename": result_file.name,
                "file_size": result_file.stat().st_size,
                "created_time": result_file.stat().st_ctime,
                "download_url": f"{cnf.fs}/download/{sha1_hash}/{result_file.name}",
            }
        )

    return {"sha1_hash": sha1_hash, "result_count": len(results), "results": results}


@router.get("/download/{sha1_hash}/{filename}")
async def download_result_file(sha1_hash: str, filename: str, lines: int = 0):
    """Download a result file."""
    from fastapi.responses import StreamingResponse

    storage_dir = cnf.fs_workdir / sha1_hash / OUT
    file_path = storage_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if lines > 10:
        # Create CSV content in memory and stream it
        from app.utils.file_utils import csv2first_n_rows_memory

        csv_io = csv2first_n_rows_memory(str(file_path), lines)
        csv_content = csv_io.getvalue()

        def iter_content():
            yield csv_content.encode("utf-8")

        return StreamingResponse(
            iter_content(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    return FileResponse(path=str(file_path), filename=filename, media_type="text/csv")


@router.get("/metadata/{sha1_hash}/{filename}")
async def get_metadata_json(sha1_hash: str, filename: str):
    """Return a metadata JSON file parsed and served with application/json."""
    storage_dir = cnf.fs_workdir / sha1_hash

    if not storage_dir.exists():
        raise HTTPException(status_code=404, detail="Directory not found")

    metadata_path = storage_dir / filename
    if not metadata_path.exists() or metadata_path.suffix.lower() != ".json":
        raise HTTPException(status_code=404, detail="Metadata file not found")

    try:
        import json

        with open(metadata_path, "r") as f:
            data = json.load(f)

        return JSONResponse(content=data, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading metadata: {str(e)}")


@router.delete("/remove/{sha1_hash}")
async def remove_file(sha1_hash: str):
    """Remove a file and all its results by SHA1 hash."""
    storage_dir = cnf.fs_workdir / sha1_hash

    if not storage_dir.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        shutil.rmtree(storage_dir)
        return {"message": f"File with SHA1 hash {sha1_hash} removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing file: {str(e)}")


@router.delete("/remove_all")
async def remove_all_files(
    delete_pass: str = Query(..., description="Password for deletion"),
):
    """Remove all uploaded files and results."""
    if delete_pass != "123":
        raise HTTPException(status_code=403, detail="Unauthorized")

    if not cnf.fs_workdir.exists():
        raise HTTPException(status_code=404, detail="No files found")

    try:
        shutil.rmtree(cnf.fs_workdir)
        return {"message": "All files removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing files: {str(e)}")


@router.get("/meta/{sha1_hash}")
async def get_meta(sha1_hash: str):
    """Get service metadata like version, description, etc."""
    proper_dir = cnf.fs_workdir / sha1_hash
    meta = get_metadata(proper_dir)
    return meta
