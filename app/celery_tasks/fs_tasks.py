import json
import time
from pathlib import Path
from typing import List

from app.config import cnf
from app.dimensionality_reduction import pca
from app.utils.algorithm_utils import fs_wrapper
from app.utils.get_metadata import get_metadata
from app.utils.json_utils import serialize_for_json

from ..cpg2gene.cpg_gene_mapping import (
    build_gene_names_df,
)

# from ..algorithms.selector import ALGORITHMS
from ..services.get_algorithms import get_algorithm
from .celery import app

PROGNOSIS_COLUMN = cnf.prognosis_column_name
OUT = cnf.fs_outdir_name


def notify_progress(task, status: str, progress: int):
    """Helper to update Celery task state."""
    task.update_state(state="PROCESSING", meta={"status": status, "progress": progress})


def notify_warning(task, warning: str, progress: int = 95):
    """Helper to update Celery task state with a warning."""
    task.update_state(
        state="PROCESSING",
        meta={
            "status": f"Warning: Gene mapping failed - {warning}. Saving results without gene names.",
            "progress": progress,
            "warning": warning,
            "gene_mapping_warning": warning,
        },
    )


@app.task(bind=True)
def process_prognosis_algorithm(
    self,
    file_path: str,
    sha1_hash: str,
    storage_dir: str,
    selected_prognosis: List[str],
    algorithm: str,
    keep_features: int,
):
    """
    Run feature ranking algorithm on selected prognosis values.
    This is a heavy task that processes the data and generates feature rankings.
    """
    try:
        algorithm_func = get_algorithm(algorithm)

        results = fs_wrapper(
            algorithm=algorithm_func,
            csv_path=file_path,
            selected_prognosis=selected_prognosis,
            parent=self,
        )
        notify_progress(self, "Saving  results", 80)

        # Create output filename
        output_filename, output_path, json_path, plot_path = generate_output_paths(
            storage_dir, selected_prognosis, algorithm, keep_features
        )

        pca_plot = pca.pca_plot(
            df=results["df"],
            conditions=selected_prognosis,
            fs_algorithm_name=algorithm,
            selected_features=results["feature_ranking"]["Feature"]
            .head(keep_features)
            .tolist(),
            n_components=2,
        )
        pca_plot.savefig(plot_path, dpi=300, bbox_inches="tight")

        metadata = get_metadata(Path(file_path).parent)
        illumina_type = metadata["detected_illumina_array_types"][0]

        gene_mapping_warning = None
        try:
            # guessed_type = guess_type(results["feature_ranking"])
            feature_with_gene_df = build_gene_names_df(
                array_type=illumina_type, feature_df=results["feature_ranking"]
            )
            # Save feature ranking results with gene mapping
            feature_with_gene_df.to_csv(output_path, index=False)
        except ValueError as ge:
            # Record the warning and save raw feature ranking without gene names
            gene_mapping_warning = str(ge)
            notify_warning(self, gene_mapping_warning)
            results["feature_ranking"].to_csv(output_path, index=False)

        # Prepare final results
        final_results = {
            "sha1_hash": sha1_hash,
            "algorithm": algorithm,
            "all_prognosis_values": results["all_prognosis"],
            "selected_prognosis_values": selected_prognosis,
            "illumina_array_type": illumina_type,
            "output_filename": output_filename,
            "total_samples": results["total_samples"],
            "features_ranked": results["features_ranked"],
            "numeric_features_used": results["numeric_features_used"],
            "class_mapping": results.get("class_mapping", {}),
            "processing_time": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        }

        if gene_mapping_warning:
            final_results["gene_mapping_warning"] = gene_mapping_warning

        notify_success(self, gene_mapping_warning)

        write_json(json_path, final_results)
        return serialize_for_json(final_results)

    except Exception as exc:
        notify_failure(
            self, selected_prognosis, algorithm, str(exc), type(exc).__name__
        )
        raise


def notify_failure(self, selected_prognosis, algorithm, error_msg, exc_type):
    self.update_state(
        state="FAILURE",
        meta={
            "status": f"Error processing algorithm: {error_msg}",
            "error": error_msg,
            "exc_type": exc_type,
            "exc_message": error_msg,
            "algorithm": algorithm,
            "selected_prognosis": selected_prognosis,
        },
    )


def notify_success(self, gene_mapping_warning):
    success_meta = {"status": "Feature ranking completed", "progress": 100}
    if gene_mapping_warning:
        success_meta["warning"] = gene_mapping_warning
        success_meta["gene_mapping_warning"] = gene_mapping_warning

    self.update_state(state="SUCCESS", meta=success_meta)


def write_json(json_path, final_results):
    with open(json_path, "w") as f:
        json.dump(serialize_for_json(final_results), f, indent=2, default=str)


def generate_output_paths(storage_dir, selected_prognosis, algorithm, keep_features):
    selected_values_str = "_".join(selected_prognosis)
    output_filename = f"{algorithm}_{selected_values_str}_results.csv"
    save_path = Path(storage_dir) / OUT

    save_path.mkdir(parents=True, exist_ok=True)

    output_path = save_path / output_filename
    json_path = save_path / f"{algorithm}_{selected_values_str}_results.json"
    plot_path = (
        save_path
        / f"{algorithm}_{selected_values_str}_pca_{keep_features}_features.png"
    )

    return output_filename, output_path, json_path, plot_path


@app.task
def cleanup_old_prognosis_files(days_old: int = 30):
    """
    Cleanup task to remove old prognosis analysis files.
    """
    import shutil
    import time
    from pathlib import Path

    upload_dir = Path("prognosis_uploads")
    if not upload_dir.exists():
        return {"message": "Prognosis upload directory doesn't exist"}

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
