import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.feature_selection import f_classif


def anova_ftest(df: pd.DataFrame, *, label_col: str = "Prognosis") -> pd.DataFrame:
    """
    Rank ALL features (best → worst) using a simple statistical test:
      - multiclass & binary: one-way ANOVA F-test (f_classif)
        (for binary, F = t^2, i.e., equivalent to two-sample t-test ranking)

    Assumes:
      - df[label_col] already encoded (ints 0..K-1)
      - feature columns are numeric (e.g., 0..1)

    Returns:
      pd.DataFrame with a single column 'Feature' ordered best → worst.
    """
    if label_col not in df.columns:
        raise ValueError(f"Label column '{label_col}' not found.")

    y = df[label_col].to_numpy()
    X = df.drop(columns=[label_col])

    if not np.issubdtype(y.dtype, np.number):
        raise ValueError(f"'{label_col}' must be numeric/encoded already.")

    nonnum = [c for c in X.columns if not is_numeric_dtype(X[c])]
    if nonnum:
        raise ValueError(
            f"Non-numeric feature columns found: {nonnum}. Encode/convert first."
        )

    classes = np.unique(y)
    if len(classes) < 2:
        raise ValueError("Need at least two classes in the target.")

    # ANOVA F (handles binary & multiclass)
    F, p = f_classif(X.values, y)

    # Clean up edge cases (constant features, etc.)
    F = np.nan_to_num(F, nan=0.0, posinf=0.0, neginf=0.0)
    p = np.nan_to_num(p, nan=1.0, posinf=1.0, neginf=1.0)

    feats = np.array(X.columns)

    # Strict order: primary = F desc, secondary = p asc, tertiary = name asc
    order_idx = np.lexsort((feats, p, -F))
    return pd.DataFrame({"Feature": feats[order_idx], "Importance": F[order_idx]})
