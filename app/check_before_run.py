from pathlib import Path

from app.config import cnf


def check_if_pkl_files_exist() -> bool:
    pkl_dir = Path(__file__).parent.parent / "pkl"

    required_files = cnf.manifest_pkl
    missing_files = [f for f in required_files if not (pkl_dir / f).exists()]
    if missing_files:
        print(f"❌ Missing .pkl files: {', '.join(missing_files)}")
        return False
    print("✔️  All required .pkl files are present.")
    return True


def dummy_check() -> bool:
    print("✔️  Dummy check passed.")
    return True


def check() -> bool:
    return all(
        [
            check_if_pkl_files_exist(),
            dummy_check(),
        ]
    )
