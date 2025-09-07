from pathlib import Path

import pandas as pd

from app.config import cnf

current_path = Path(__file__).parent.resolve()


def csv2pickle(csv_path):
    try:
        df = pd.read_csv(csv_path)
        df = df[["CpG_site", "GeneName"]]
        file_name = Path(csv_path).stem
        file_path = current_path / f"{file_name}.pkl"
        df.to_pickle(file_path)
        print(f"Created {file_path}")
    except Exception as e:
        print(f"Error processing {csv_path}: {e}")


def create_pickles_in_current_directory(*, csv_dir):
    file_path = Path(csv_dir)
    for manifest in cnf.manifest_csv:
        if not (file_path / manifest).exists():
            raise FileNotFoundError(f"{manifest} not found in {file_path}")
        csv2pickle(file_path / manifest)


if __name__ == "__main__":
    print(f"Creating pickles in {current_path}")
    create_pickles_in_current_directory(csv_dir="Directory with the 3 csv files")
