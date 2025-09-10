from pathlib import Path

import docker
from app.config import cnf

from ..cpg2gene.cpg_gene_mapping import build_gene_names_using_csv
from ..utils.get_metadata import get_metadata
from .celery import app


def _docker_out_csv(condition_1, condition_2, delta_beta, p_value):
    """Generate the expected output CSV filename from the Docker DMP analysis."""
    return f"dmps_{condition_1}_vs_{condition_2}_db{delta_beta}_pval{p_value}.csv"


def _validate_and_prepare_paths(storage_dir: str, docker_csv_name: str):
    """Validate input directory and prepare output paths.

    Returns a tuple (input_path, output_path, docker_csv_path, csv_with_genes_path)
    or raises FileNotFoundError if input directory missing.
    """
    storage_path = Path(storage_dir).resolve()
    input_path = storage_path
    output_path = storage_path / "out"
    output_path.mkdir(parents=True, exist_ok=True)
    docker_csv_path = output_path / docker_csv_name
    csv_with_genes_path = output_path / f"{docker_csv_name}_with_genes.csv"

    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_path}")

    return input_path, output_path, docker_csv_path, csv_with_genes_path


def _ensure_docker_ready(r_docker_image: str):
    """Ensure Docker daemon is reachable and image exists. Returns docker client.

    Raises docker.errors.DockerException or docker.errors.ImageNotFound.
    """
    client = docker.from_env()
    client.ping()
    client.images.get(r_docker_image)
    return client


def _run_docker_analysis(client, r_docker_image, volumes, command):
    """Run the docker container and return logs (bytes or str).

    Raises docker.errors.ContainerError or docker.errors.APIError.
    """
    return client.containers.run(
        r_docker_image, remove=True, detach=False, volumes=volumes, command=command
    )


def _enrich_csv_with_genes(
    storage_path: Path, docker_csv_path: Path, csv_with_genes_path: Path
):
    """Call metadata reader and gene-mapping to enrich the docker CSV with gene names.

    Raises any errors from metadata or mapping functions.
    """
    metadata = get_metadata(storage_path)
    illumina_type = metadata["detected_illumina_array_types"][0]

    build_gene_names_using_csv(
        array_type=illumina_type,
        feature_csv_path=str(docker_csv_path),
        csv_with_genes_path=str(csv_with_genes_path),
        fno=0,
    )


@app.task(bind=True)
def dmp_selection_task(
    self,
    storage_dir: str,
    condition_1: str,
    condition_2: str,
    delta_beta: float = 0.4,
    p_value: float = 0.05,
):
    """
    Task to perform Differentially Methylated Positions (DMP) analysis.
    This is a heavy task that processes the data and identifies DMPs.
    """
    self.update_state(
        state="PROCESSING", meta={"status": "Loading data", "progress": 0}
    )

    docker_csv_name = _docker_out_csv(condition_1, condition_2, delta_beta, p_value)

    try:
        input_path, output_path, docker_csv_path, csv_with_genes_path = (
            _validate_and_prepare_paths(storage_dir, docker_csv_name)
        )
    except FileNotFoundError as e:
        return {
            "status": "error",
            "error": str(e),
            "message": 'Files should be in the "in" subdirectory',
        }

    # Ensure Docker is available and image exists
    try:
        client = _ensure_docker_ready(cnf.r_docker_image)
    except docker.errors.ImageNotFound:
        return {
            "status": "error",
            "error": f"Docker image {cnf.r_docker_image} not found",
            "message": "Build the image first",
        }
    except docker.errors.DockerException as e:
        return {
            "status": "error",
            "error": f"Docker connection failed: {str(e)}",
            "message": "Make sure Docker is running and accessible",
        }

    volumes, command = _docker_params(
        condition_1, condition_2, delta_beta, p_value, input_path, output_path
    )

    try:
        container_logs = _run_docker_analysis(
            client, cnf.r_docker_image, volumes, command
        )

        # Enrich docker CSV with gene names
        try:
            _enrich_csv_with_genes(
                Path(storage_dir).resolve(), docker_csv_path, csv_with_genes_path
            )
        except Exception as e:
            return {"status": "error", "error": f"Failed to enrich CSV: {str(e)}"}

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


def _docker_params(
    condition_1, condition_2, delta_beta, p_value, input_path, output_path
):
    volumes = {
        str(input_path): {"bind": "/input", "mode": "ro"},
        str(output_path): {"bind": "/output", "mode": "rw"},
    }

    command = [
        "dmp_volcano.R",
        "--condition1",
        condition_1,
        "--condition2",
        condition_2,
        "--delta_beta",
        str(delta_beta),
        "--p_value",
        str(p_value),
    ]

    return volumes, command
