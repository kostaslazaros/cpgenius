import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List

import docker
from app.config import cnf

from .celery import app


@app.task(bind=True)
def process_uploaded_files(
    self, file_paths: List[str], sha1_hash: str, storage_dir: str
):
    """
    Process uploaded .idat and .csv files.
    This is a long-running task that can be extended with specific processing logic.
    """
    try:
        # Update task state
        self.update_state(
            state="PROCESSING",
            meta={"status": "Starting file processing", "progress": 0},
        )

        results = {
            "sha1_hash": sha1_hash,
            "storage_dir": storage_dir,
            "files_processed": [],
            "processing_summary": {},
            "start_time": time.time(),
        }

        # Docker processing with better error handling
        docker_result = run_docker_processing(
            storage_dir=storage_dir, command=["idat_preprocessor.R"]
        )
        results["docker_processing"] = docker_result

        # Final state update
        self.update_state(
            state="SUCCESS",
            meta={"status": "File processing completed", "progress": 100},
        )

        return results

    except Exception as exc:
        # Update task state with error
        self.update_state(
            state="FAILURE",
            meta={"status": f"Error processing files: {str(exc)}", "error": str(exc)},
        )
        raise exc


def run_docker_processing(*, storage_dir: str, command: list[str]) -> Dict[str, Any]:
    """
    Run Docker container processing with proper error handling.
    """
    try:
        # Ensure absolute paths - input files are in storage_dir/in/
        storage_path = Path(storage_dir).resolve()
        input_path = storage_path / "in"  # Files are in the 'in' subdirectory
        output_path = storage_path / "out"
        output_path.mkdir(parents=True, exist_ok=True)
        volumes = {
            str(input_path): {"bind": "/input", "mode": "ro"},
            str(output_path): {"bind": "/output", "mode": "rw"},
        }
        # Check if input directory exists and has files
        if not input_path.exists():
            return {
                "status": "error",
                "error": f"Input directory not found: {input_path}",
                "message": 'Files should be in the "in" subdirectory',
            }

        try:
            client = docker.from_env()
            # Test Docker connection
            client.ping()
        except docker.errors.DockerException as e:
            return {
                "status": "error",
                "error": f"Docker connection failed: {str(e)}",
                "message": "Make sure Docker is running and accessible",
            }

        try:
            client.images.get(cnf.r_docker_image)
        except docker.errors.ImageNotFound:
            return {
                "status": "error",
                "error": f"Docker image {cnf.r_docker_image} not found",
                "message": "Build the image first",
            }

        # Run container with proper error handling
        try:
            container_logs = client.containers.run(
                cnf.r_docker_image,
                remove=True,
                detach=False,
                volumes=volumes,
                command=command,
            )

            return {
                "status": "success",
                "logs": container_logs.decode("utf-8")
                if isinstance(container_logs, bytes)
                else str(container_logs),
                "input_dir": str(input_path),
                "output_dir": str(output_path),
                "message": "Docker processing completed successfully",
            }

        except docker.errors.ContainerError as e:
            return {
                "status": "error",
                "error": f"Container execution failed: {str(e)}",
                "exit_code": e.exit_status,
                "logs": e.stderr.decode("utf-8") if e.stderr else "No error logs",
            }
        except docker.errors.APIError as e:
            return {
                "status": "error",
                "error": f"Docker API error: {str(e)}",
                "message": "Check Docker daemon and permissions",
            }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected Docker error: {str(e)}",
            "message": "Check Docker installation and permissions",
        }


def process_individual_file(file_path: Path) -> Dict[str, Any]:
    """
    Process an individual file (.idat or .csv).
    Extend this function with your specific processing logic.
    """
    try:
        file_stats = file_path.stat()

        # Calculate file hash for integrity verification
        file_hash = calculate_file_hash(file_path)

        # Basic file analysis
        file_result = {
            "filename": file_path.name,
            "file_path": str(file_path),
            "file_size": file_stats.st_size,
            "file_extension": file_path.suffix.lower(),
            "file_hash": file_hash,
            "processing_status": "success",
            "created_time": file_stats.st_ctime,
            "modified_time": file_stats.st_mtime,
        }

        # Specific processing based on file type
        if file_path.suffix.lower() == ".csv":
            file_result.update(process_csv_file(file_path))
        elif file_path.suffix.lower() == ".idat":
            file_result.update(process_idat_file(file_path))

        return file_result

    except Exception as e:
        return {
            "filename": file_path.name,
            "file_path": str(file_path),
            "processing_status": "error",
            "error": str(e),
        }


def process_csv_file(file_path: Path) -> Dict[str, Any]:
    """
    Process CSV file - extend with your specific logic.
    """
    try:
        # Basic CSV analysis
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        return {
            "file_type_analysis": {
                "total_lines": len(lines),
                "header_line": lines[0].strip() if lines else "",
                "estimated_columns": len(lines[0].split(",")) if lines else 0,
                "sample_data": lines[1].strip() if len(lines) > 1 else "",
            }
        }
    except Exception as e:
        return {"csv_processing_error": str(e)}


def process_idat_file(file_path: Path) -> Dict[str, Any]:
    """
    Process IDAT file - extend with your specific logic.
    Note: IDAT files are typically binary files used in bioinformatics.
    """
    try:
        # Basic binary file analysis
        with open(file_path, "rb") as f:
            # Read first few bytes to analyze file structure
            header = f.read(100)

        return {
            "file_type_analysis": {
                "file_format": "IDAT (Binary)",
                "header_bytes": len(header),
                "header_sample": header[:20].hex() if header else "",
                "is_binary": True,
            }
        }
    except Exception as e:
        return {"idat_processing_error": str(e)}


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of individual file for integrity verification."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def generate_processing_summary(
    files_processed: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate a summary of the file processing results."""
    total_files = len(files_processed)
    successful_files = len(
        [f for f in files_processed if f.get("processing_status") == "success"]
    )
    failed_files = total_files - successful_files

    total_size = sum(
        f.get("file_size", 0) for f in files_processed if f.get("file_size")
    )

    file_types = {}
    for file_info in files_processed:
        ext = file_info.get("file_extension", "unknown")
        file_types[ext] = file_types.get(ext, 0) + 1

    return {
        "total_files": total_files,
        "successful_files": successful_files,
        "failed_files": failed_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "file_types": file_types,
        "success_rate": round((successful_files / total_files) * 100, 2)
        if total_files > 0
        else 0,
    }


@app.task
def cleanup_old_files(days_old: int = 30):
    """
    Cleanup task to remove files older than specified days.
    This can be run periodically to manage storage space.
    """
    import shutil
    import time
    from pathlib import Path

    upload_dir = Path("uploads")
    if not upload_dir.exists():
        return {"message": "Upload directory doesn't exist"}

    current_time = time.time()
    cutoff_time = current_time - (days_old * 24 * 60 * 60)

    removed_directories = []
    total_size_freed = 0

    for dir_path in upload_dir.iterdir():
        if dir_path.is_dir():
            dir_mtime = dir_path.stat().st_mtime
            if dir_mtime < cutoff_time:
                # Calculate directory size before removal
                dir_size = sum(
                    f.stat().st_size for f in dir_path.rglob("*") if f.is_file()
                )
                total_size_freed += dir_size

                shutil.rmtree(dir_path)
                removed_directories.append(
                    {
                        "sha1_hash": dir_path.name,
                        "size_bytes": dir_size,
                        "age_days": (current_time - dir_mtime) / (24 * 60 * 60),
                    }
                )

    return {
        "removed_directories": len(removed_directories),
        "total_size_freed_mb": round(total_size_freed / (1024 * 1024), 2),
        "directories": removed_directories,
    }
