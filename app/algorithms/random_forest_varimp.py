import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.ensemble import RandomForestClassifier


def random_forest_varimp(
    df: pd.DataFrame,
    *,
    label_col: str = "Prognosis",
    n_estimators: int = 300,
    max_depth: int = None,
    max_features="sqrt",  # good default for classification
    min_samples_leaf: int = 1,
    bootstrap: bool = True,
    max_samples=None,  # e.g., 0.5–0.8 to speed up on large datasets
    random_state: int = 0,
    n_jobs: int = -1,
) -> pd.DataFrame:
    """
    Rank ALL features (best → worst) using RandomForest variable importance.

    Assumes:
      - df[label_col] is ALREADY encoded (e.g., ints 0..K-1),
      - feature columns are numeric (e.g., 0..1).

    Returns:
      pd.DataFrame: single column 'Feature' ordered best → worst by importance.
    """
    if label_col not in df.columns:
        raise ValueError(
            f"Label column '{label_col}' not found. Columns: {list(df.columns)}"
        )

    y = df[label_col].to_numpy()
    X = df.drop(columns=[label_col])

    # sanity checks
    if not np.issubdtype(y.dtype, np.number):
        raise ValueError(f"'{label_col}' must be numeric/encoded already.")
    nonnum = [c for c in X.columns if not is_numeric_dtype(X[c])]
    if nonnum:
        raise ValueError(
            f"Non-numeric feature columns found: {nonnum}. Encode/convert them first."
        )
    if len(np.unique(y)) < 2:
        raise ValueError("Need at least two classes in the target.")

    rf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        max_features=max_features,
        min_samples_leaf=min_samples_leaf,
        class_weight="balanced",
        bootstrap=bootstrap,
        max_samples=max_samples,
        random_state=random_state,
        n_jobs=n_jobs,
    )

    rf.fit(X, y)
    importances = rf.feature_importances_
    order = np.argsort(-importances)  # descending

    return pd.DataFrame({"Feature": X.columns[order], "Importance": importances[order]})
