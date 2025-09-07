import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.feature_selection import RFE
from sklearn.svm import LinearSVC


def rfe_svm(
    df: pd.DataFrame,
    *,
    label_col: str = "Prognosis",
    # Tighter regularization → faster convergence; you can raise to 0.2–1.0 if needed
    C: float = 0.1,
    # Huge fractional step = drop ~99% per round → ~5–7 fits total for 300k cols
    step: float = 0.99,
    # Looser tolerance → fewer solver iterations per fit
    tol: float = 5e-2,
    random_state: int = 0,
    # Plenty for convergence with tol=5e-2; bump if you see ConvergenceWarning
    max_iter: int = 5000,
    # Usually faster than squared_hinge for this use
    loss: str = "hinge",
    # Avoids per-iteration class reweighting cost unless you truly need it
    class_weight=None,
) -> pd.DataFrame:
    """
    Rank ALL features (best → worst) using Linear SVM + RFE, tuned for speed on p ≫ n.
    Assumes feature columns are already numeric (e.g., scaled 0..1) and `label_col` is encoded.

    Returns:
        pd.DataFrame: single column 'Feature' ordered best → worst
    """
    if label_col not in df.columns:
        raise ValueError(
            f"Label column '{label_col}' not found. Columns: {list(df.columns)}"
        )

    # Split
    y = df[label_col].to_numpy()
    X_df = df.drop(columns=[label_col])

    # Require at least 2 classes
    n_classes = len(np.unique(y))
    if n_classes < 2:
        raise ValueError(
            f"Need at least 2 classes in '{label_col}'; found {n_classes}."
        )

    # Ensure numeric features
    nonnum = [c for c in X_df.columns if not is_numeric_dtype(X_df[c])]
    if nonnum:
        raise ValueError(
            f"Non-numeric feature columns found: {nonnum}. Encode/convert them first."
        )

    # Convert to float32 to cut time/memory
    X = X_df.to_numpy(dtype=np.float32, copy=False)
    n_samples, n_features = X.shape

    # For p >> n, dual=True is appropriate (LinearSVC uses liblinear)
    dual_flag = True if n_features >= n_samples else False

    est = LinearSVC(
        dual=dual_flag,
        C=C,
        tol=tol,
        loss=loss,
        class_weight=class_weight,
        random_state=random_state,
        max_iter=max_iter,
    )

    # n_features_to_select=1 => compute a full ranking (keeps all features)
    rfe = RFE(estimator=est, n_features_to_select=1, step=step)
    rfe.fit(X, y)

    ranks = pd.Series(
        rfe.ranking_, index=X_df.columns, name="RFE_rank"
    ).sort_values()  # 1 = best
    ordered_features = ranks.index.tolist()

    return pd.DataFrame(
        {"Feature": ordered_features, "Importance": ranks[ordered_features].values},
        index=range(len(ordered_features)),
    )
