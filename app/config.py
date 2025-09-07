import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

_MANIFESTS = {
    "450k": "IlluminaHumanMethylation450k",
    "epic": "IlluminaHumanMethylationEPIC",
    "epicv2": "IlluminaHumanMethylationEPICv2",
}

PKL_DIR: Path = Path(__file__).parent.parent / "pkl"


@dataclass(frozen=True)
class Config:
    broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    backend_url: str = os.getenv("CELERY_BACKEND_URL", broker_url)
    prognosis_column_name: str = os.getenv("PROGNOSIS_COLUMN_NAME", "Prognosis")

    workdir: Path = Path(os.getenv("DATA_FOLDER", "workdir"))

    bval: str = os.getenv("PREFIX_BVAL", "bval")
    dmp: str = os.getenv("PREFIX_DMP", "dmp")
    fs: str = os.getenv("PREFIX_FS", "fs")

    prefix_bval = f"/{bval}"
    prefix_dmp = f"/{dmp}"
    prefix_fs = f"/{fs}"

    bval_workdir: Path = workdir / bval  # Beta value calculation
    dmp_workdir: Path = workdir / dmp  # Differential Methylation Analysis
    fs_workdir: Path = workdir / fs  # Feature selection
    # those are subdirectories under the sha1_hash directory
    # e.g. workdir/fs/<sha1_hash>/fsout
    bval_outdir_name: str = os.getenv("BVAL_OUT_DIR", "bvalout")
    dmp_outdir_name: str = os.getenv("DMP_OUT_DIR", "dmpout")
    fs_outdir_name: str = os.getenv("FS_OUT_DIR", "fsout")

    bval_allowed_extensions = {".idat", ".csv"}
    fs_allowed_extensions = {".csv"}
    r_docker_image: str = os.getenv("R_DOCKER_IMAGE", "konlaz/r-analysis")

    manifest_csv = [f"{name}.csv" for name in _MANIFESTS.values()]
    manifest_pkl = [f"{name}.pkl" for name in _MANIFESTS.values()]
    pkl_files = {key: PKL_DIR / f"{name}.pkl" for key, name in _MANIFESTS.items()}

    metadata_file: str = os.getenv("METADATA_FILE", "analysis42.json")

    def create_directories(self):
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.bval_workdir.mkdir(parents=True, exist_ok=True)
        self.fs_workdir.mkdir(parents=True, exist_ok=True)
        self.dmp_workdir.mkdir(parents=True, exist_ok=True)


cnf = Config()
cnf.create_directories()
