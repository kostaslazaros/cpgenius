import numpy as np
import pandas as pd


def dummy_classifier(
    df: pd.DataFrame, *, label_col: str = "Prognosis", include_label: bool = False
) -> pd.DataFrame:
    """
    Return a random ranking of features as a DataFrame with a single column 'Feature'.
    - Excludes `label_col` by default.
    - No random_state (purely random each call).
    """
    if not isinstance(df, pd.DataFrame):
        raise ValueError("df must be a pandas DataFrame.")

    cols = list(df.columns)
    if not include_label and label_col in cols:
        feats = [c for c in cols if c != label_col]
    else:
        feats = cols[
            :
        ]  # include all columns if label_col not present or include_label=True

    if len(feats) == 0:
        raise ValueError("No feature columns found to shuffle.")

    shuffled = np.random.permutation(feats)
    return pd.DataFrame(
        {"Feature": shuffled, "Importance": np.random.rand(len(shuffled))}
    )
