import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.linear_model import LogisticRegression


def lasso_lrc(
    df: pd.DataFrame,
    *,
    label_col: str = "Prognosis",
    C: float = 10.0,
    max_iter: int = 8000,
    tol: float = 1e-3,
    class_weight: str = "balanced",
    random_state: int = 0,
) -> pd.DataFrame:
    if label_col not in df.columns:
        raise ValueError(f"Label column '{label_col}' not found.")

    y = df[label_col].to_numpy()
    X = df.drop(columns=[label_col])

    if not np.issubdtype(y.dtype, np.number):
        raise ValueError(f"'{label_col}' must be numeric/encoded already.")
    nonnum = [c for c in X.columns if not is_numeric_dtype(X[c])]
    if nonnum:
        raise ValueError(f"Non-numeric feature columns found: {nonnum}.")

    classes = np.unique(y)
    if len(classes) < 2:
        raise ValueError("Need at least two classes in the target.")

    # No multi_class parameter → no FutureWarning
    clf = LogisticRegression(
        penalty="l1",
        solver="saga",
        C=C,
        max_iter=max_iter,
        tol=tol,
        class_weight=class_weight,
        random_state=random_state,
        fit_intercept=True,
    )
    clf.fit(X.values, y)

    W = clf.coef_
    coef_score = np.abs(W) if W.ndim == 1 else np.linalg.norm(W, axis=0)

    Xv = X.values.astype(float)
    n = Xv.shape[0]
    Xc = Xv - Xv.mean(axis=0, keepdims=True)
    Xs = Xv.std(axis=0, ddof=1, keepdims=True)
    Xs[Xs == 0] = 1.0

    if len(classes) == 2:
        yb = y.astype(float)
        yc = yb - yb.mean()
        ys = yb.std(ddof=1) or 1.0
        corr = (Xc.T @ yc) / ((n - 1) * (Xs.ravel() * ys))
        tie_score = np.abs(corr)
    else:
        tie_score = np.zeros(X.shape[1], dtype=float)
        for c in classes:
            yc = (y == c).astype(float)
            yc = yc - yc.mean()
            ys = yc.std(ddof=1)
            if ys == 0:
                continue
            corr_c = (Xc.T @ yc) / ((n - 1) * (Xs.ravel() * ys))
            tie_score = np.maximum(tie_score, np.abs(corr_c))

    coef_score = np.asarray(coef_score).reshape(-1)
    tie_score = np.asarray(tie_score).reshape(-1)
    feats = np.array(X.columns)

    order_idx = np.lexsort((feats, -tie_score, -coef_score))
    return pd.DataFrame(
        {"Feature": feats[order_idx], "Importance": coef_score[order_idx]}
    )
