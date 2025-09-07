"""
CSV utility functions for data processing operations.
"""

import hashlib
from io import StringIO
from pathlib import Path

import aiofiles
import pandas as pd
from fastapi import HTTPException, UploadFile

from app.config import cnf


def csv2first_n_rows(csv_file: str, num_rows: int) -> str:
    name = Path(csv_file).stem
    out = Path(csv_file).parent / f"{name}_first_{num_rows}.csv"
    pd.read_csv(csv_file, nrows=num_rows).to_csv(out, index=False)
    return str(out)


def csv2first_n_rows_memory(csv_file: str, num_rows: int) -> StringIO:
    df = pd.read_csv(csv_file, nrows=num_rows)
    csv_string = df.to_csv(index=False)
    return StringIO(csv_string)


def calculate_file_sha1(file_path: Path) -> str:
    """Calculate SHA1 hash of a single file."""
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    return sha1.hexdigest()


def calculate_sha1_hashes(file_paths: list[Path]) -> str:
    """Calculate SHA1 hash using manifest approach (matches JavaScript implementation)."""
    # Filter and sort files like JavaScript does
    filtered_files = []
    for file_path in file_paths:
        name_lower = file_path.name.lower()
        if name_lower.endswith(".csv") or name_lower.endswith(".idat"):
            filtered_files.append(file_path)

    if not filtered_files:
        return ""

    # Sort by relative path (just filename in this case)
    filtered_files.sort(key=lambda f: f.name)

    # Build manifest lines like JavaScript
    lines = []
    for file_path in filtered_files:
        # Calculate individual file SHA-1
        file_sha1 = hashlib.sha1()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                file_sha1.update(chunk)

        file_size = file_path.stat().st_size
        file_hash = file_sha1.hexdigest()

        # Format: "filename\nsize\nhash\n"
        lines.append(f"{file_path.name}\n{file_size}\n{file_hash}\n")

    # Create canonical manifest and hash it
    canonical = "".join(lines)
    manifest_sha1 = hashlib.sha1(canonical.encode("utf-8"))

    return manifest_sha1.hexdigest()


def validate_csv_file(file: UploadFile) -> bool:
    """Validate that the file is a CSV."""
    if not file.filename:
        return False

    extension = Path(file.filename).suffix.lower()
    return extension in cnf.fs_allowed_extensions


def validate_file_extensions(files: list[UploadFile]) -> bool:
    """Validate that all files have allowed extensions."""
    for file in files:
        if file.filename:
            extension = Path(file.filename).suffix.lower()
            if extension not in cnf.bval_allowed_extensions:
                return False
    return True


async def save_csv_file(file: UploadFile, temp_dir: Path) -> Path:
    """Save uploaded CSV file to temporary directory."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    file_path = temp_dir / file.filename

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    return file_path


async def save_uploaded_files(files: list[UploadFile], temp_dir: Path) -> list[Path]:
    """Save uploaded files to temporary directory and return file paths."""
    saved_files = []

    for file in files:
        if not file.filename:
            continue

        file_path = temp_dir / file.filename

        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        saved_files.append(file_path)

        # Reset file pointer for potential re-use
        await file.seek(0)

    return saved_files
