# Beta Value Creation Router
# Handles uploading .idat and .csv files, processing them to generate beta values,
# and managing the resulting files and images.
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.celery_tasks.bval_tasks import process_uploaded_files
from app.config import cnf
from app.schemas import FileProcessingStatus, FileUploadResponse
from app.utils.file_utils import (
    calculate_sha1_hashes,
    save_uploaded_files,
    validate_file_extensions,
)

router = APIRouter(prefix=cnf.prefix_bval, tags=["Beta Value Creation"])

# Configuration
# UPLOAD_DIR = Path("uploads")
UPLOAD_DIR = cnf.bval_workdir


@router.post("/upload", response_model=FileUploadResponse)
async def upload_files(
    files: list[UploadFile] = File(..., description="Upload .idat and .csv files"),
    bundle_id: str = Form(None),
    file_count: int = Form(None),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Validate file extensions
    if not validate_file_extensions(files):
        raise HTTPException(
            status_code=400,
            detail=f"Only files with extensions {cnf.bval_allowed_extensions} are allowed",
        )

    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        try:
            # Save files temporarily
            saved_files = await save_uploaded_files(files, temp_path)

            if not saved_files:
                raise HTTPException(status_code=400, detail="No valid files to process")

            # Calculate SHA1 hash of all files (use provided bundle_id if available)
            if bundle_id:
                sha1_hash = bundle_id
                # Optionally verify the bundle_id matches by recalculating
                calculated_hash = calculate_sha1_hashes(saved_files)
                if calculated_hash != bundle_id:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Provided bundle_id does not match calculated hash. Expected: {calculated_hash}, Got: {bundle_id}",
                    )
            else:
                sha1_hash = calculate_sha1_hashes(saved_files)

            # Create permanent storage directory
            storage_dir = UPLOAD_DIR / sha1_hash
            storage_in = storage_dir / "in"

            # Check if files already exist (check the 'in' subdirectory specifically)
            if storage_in.exists() and any(storage_in.iterdir()):
                return FileUploadResponse(
                    task_id="",
                    sha1_hash=sha1_hash,
                    message="Files with this SHA1 hash already exist",
                    file_count=len(saved_files),
                )

            # Create directories
            storage_in.mkdir(parents=True, exist_ok=True)

            # Move files to permanent storage
            final_file_paths = []
            for file_path in saved_files:
                final_path = storage_in / file_path.name
                shutil.copy2(file_path, final_path)
                final_file_paths.append(str(final_path))

            # Start Celery task for processing
            task = process_uploaded_files.delay(
                file_paths=final_file_paths,
                sha1_hash=sha1_hash,
                storage_dir=str(storage_dir),
            )

            return FileUploadResponse(
                task_id=task.id,
                sha1_hash=sha1_hash,
                message="Files uploaded successfully. Processing started.",
                file_count=len(final_file_paths),
            )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error processing files: {str(e)}"
            )


@router.get("/exists/{hash_id}")
async def get_hash_exists(hash_id: str):
    """Check if files with the given SHA1 hash already exist."""
    storage_dir = UPLOAD_DIR / hash_id
    storage_in = storage_dir / "in"

    # Check if the directory exists and contains files
    if storage_in.exists() and any(storage_in.iterdir()):
        return {"exists": True, "message": "Bundle exists"}

    # Also check old structure (files directly in hash directory)
    if storage_dir.exists() and any(f.is_file() for f in storage_dir.iterdir()):
        return {"exists": True, "message": "Bundle exists"}

    raise HTTPException(status_code=404, detail="Bundle not found")


@router.get("/status/{task_id}", response_model=FileProcessingStatus)
async def get_processing_status(task_id: str):
    """Get the status of a file processing task."""
    from app.celery_tasks.celery import app as celery_app

    try:
        task_result = celery_app.AsyncResult(task_id)

        status_response = FileProcessingStatus(
            task_id=task_id, status=task_result.status
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
    """List all uploaded file directories by SHA1 hash."""
    if not UPLOAD_DIR.exists():
        return {"directories": []}

    directories = []
    for dir_path in UPLOAD_DIR.iterdir():
        if dir_path.is_dir():
            # Look for files in the 'in' subdirectory
            in_dir = dir_path / "in"
            if in_dir.exists():
                files = [f for f in in_dir.iterdir() if f.is_file()]
                directories.append(
                    {
                        "sha1_hash": dir_path.name,
                        "file_count": len(files),
                        "files": [f.name for f in files],
                        "created_time": dir_path.stat().st_ctime,
                    }
                )
            else:
                # Fallback to old structure if 'in' directory doesn't exist
                files = [f for f in dir_path.iterdir() if f.is_file()]
                directories.append(
                    {
                        "sha1_hash": dir_path.name,
                        "file_count": len(files),
                        "files": [f.name for f in files],
                        "created_time": dir_path.stat().st_ctime,
                    }
                )

    return {"directories": directories}


@router.delete("/remove/{sha1_hash}")
async def remove_files(sha1_hash: str):
    """Remove files associated with a SHA1 hash."""
    storage_dir = UPLOAD_DIR / sha1_hash

    if not storage_dir.exists():
        raise HTTPException(status_code=404, detail="Files not found")

    try:
        shutil.rmtree(storage_dir)
        return {"message": f"Files with SHA1 hash {sha1_hash} removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing files: {str(e)}")


@router.delete("/remove_all")
async def remove_all_files(delete_pass: str):
    if delete_pass != "123":
        raise HTTPException(status_code=403, detail="Unauthorized")

    """Remove all uploaded files."""
    if not UPLOAD_DIR.exists():
        raise HTTPException(status_code=404, detail="No files found")

    try:
        shutil.rmtree(UPLOAD_DIR)
        return {"message": "All uploaded files removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing files: {str(e)}")


@router.get("/images/{sha1_hash}")
async def get_generated_images(sha1_hash: str):
    """Get list of generated PNG images from the out directory."""
    # PNG images are generated by IDAT processing and stored in uploads/sha1/out
    # uploads_dir = cnf.bval_workdir
    storage_dir = cnf.bval_workdir / sha1_hash / "out"

    if not storage_dir.exists():
        return {"sha1_hash": sha1_hash, "image_count": 0, "images": []}

    images = []
    for image_file in storage_dir.glob("*.png"):
        images.append(
            {
                "filename": image_file.name,
                "file_size": image_file.stat().st_size,
                "created_time": image_file.stat().st_ctime,
                "image_url": f"{cnf.bval}/image/{sha1_hash}/{image_file.name}",
            }
        )

    # Sort images by filename for consistent ordering
    images.sort(key=lambda x: x["filename"])

    return {"sha1_hash": sha1_hash, "image_count": len(images), "images": images}


@router.get("/metadata-status/{sha1_hash}")
async def check_metadata_status(sha1_hash: str):
    """Check if processing is complete by verifying metadata.json exists."""
    storage_dir = cnf.bval_workdir / sha1_hash / "out"
    metadata_file = storage_dir / "metadata.json"

    if not storage_dir.exists():
        return {
            "sha1_hash": sha1_hash,
            "processing_complete": False,
            "metadata_exists": False,
        }

    metadata_exists = metadata_file.exists()
    return {
        "sha1_hash": sha1_hash,
        "processing_complete": metadata_exists,
        "metadata_exists": metadata_exists,
    }


@router.get("/download-all/{sha1_hash}")
async def download_all_images(sha1_hash: str):
    """Download all PNG images and CSV files from the out directory as a ZIP file."""
    import tempfile
    import zipfile

    storage_dir = cnf.bval_workdir / sha1_hash / "out"

    if not storage_dir.exists():
        raise HTTPException(
            status_code=404, detail="No output directory found for this analysis"
        )

    # Get PNG files
    png_files = list(storage_dir.glob("*.png"))

    # Get specific CSV files
    other_files = []
    for csv_name in ["metadata.json", "bval_data.csv"]:
        csv_path = storage_dir / csv_name
        if csv_path.exists():
            other_files.append(csv_path)

    all_files = png_files + other_files

    if not all_files:
        raise HTTPException(status_code=404, detail="No PNG or CSV files found")

    # Create a temporary ZIP file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")

    try:
        with zipfile.ZipFile(temp_file.name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in all_files:
                zipf.write(file_path, file_path.name)

        temp_file.close()
        return FileResponse(
            path=temp_file.name,
            filename=f"analysis_results_{sha1_hash}.zip",
            media_type="application/zip",
        )
    except Exception as e:
        # Clean up temp file if something goes wrong
        import os

        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise HTTPException(
            status_code=500, detail=f"Error creating ZIP file: {str(e)}"
        )


@router.get("/image/{sha1_hash}/{filename}")
async def serve_generated_image(sha1_hash: str, filename: str):
    """Serve a generated PNG image."""

    # PNG images are generated by IDAT processing and stored in uploads/sha1/out
    storage_dir = cnf.bval_workdir / sha1_hash / "out"
    image_path = storage_dir / filename

    if not image_path.exists() or not image_path.suffix.lower() == ".png":
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(path=str(image_path), filename=filename, media_type="image/png")
