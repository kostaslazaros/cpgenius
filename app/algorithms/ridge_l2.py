import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.linear_model import RidgeClassifier


def ridge_l2(
    df: pd.DataFrame,
    *,
    label_col: str = "Prognosis",
    alpha: float = 1.0,
    n_repeats: int = 50,
    subsample_frac: float = 0.7,
) -> pd.DataFrame:
    """
    Rank ALL features (best → worst) using RidgeClassifier stability scores.
    - Fit the model on many random row subsamples.
    - Average the absolute value of coefficients across runs.
    - Works for binary & multiclass (one-vs-rest under the hood).

    Args:
        df: DataFrame with numeric features and encoded target.
        label_col: Name of target column.
        alpha: L2 regularization strength.
        n_repeats: Number of random subsamples to average over.
        subsample_frac: Fraction of rows to use per subsample.

    Returns:
        pd.DataFrame with a single column 'Feature' ordered best → worst.
    """
    if label_col not in df.columns:
        raise ValueError(f"Label column '{label_col}' not found in DataFrame.")

    y = df[label_col].to_numpy()
    X = df.drop(columns=[label_col])

    # Ensure numeric target and features
    if not np.issubdtype(y.dtype, np.number):
        raise ValueError(
            f"Target '{label_col}' must be numeric/encoded before calling."
        )
    nonnum = [c for c in X.columns if not is_numeric_dtype(X[c])]
    if nonnum:
        raise ValueError(f"Non-numeric feature columns found: {nonnum}")

    if len(np.unique(y)) < 2:
        raise ValueError("Need at least two classes in the target.")

    n_rows, n_feats = X.shape
    coef_accum = np.zeros(n_feats)

    for _ in range(n_repeats):
        idx = np.random.choice(n_rows, size=int(n_rows * subsample_frac), replace=False)
        X_sub, y_sub = X.iloc[idx].values, y[idx]

        model = RidgeClassifier(alpha=alpha)
        model.fit(X_sub, y_sub)

        # Handle binary vs multiclass coef_ shape
        coefs = model.coef_
        if coefs.ndim == 1:  # binary
            abs_coefs = np.abs(coefs)
        else:  # multiclass → take mean across classes
            abs_coefs = np.mean(np.abs(coefs), axis=0)

        coef_accum += abs_coefs

    # Average over repeats
    stability_scores = coef_accum / n_repeats

    # Rank features
    feats = np.array(X.columns)
    order_idx = np.lexsort((feats, -stability_scores))
    return pd.DataFrame(
        {"Feature": feats[order_idx], "Importance": stability_scores[order_idx]}
    )
