import json
from pathlib import Path

from app.config import cnf


def get_metadata(storage_dir: str) -> dict:
    metadata_path = Path(storage_dir) / cnf.metadata_file
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    return metadata
