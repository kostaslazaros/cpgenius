import numpy as np
import pandas as pd

# import shap  # not needed when using pred_contribs
from pandas.api.types import is_numeric_dtype
from xgboost import DMatrix, XGBClassifier


def shap_xgboost(
    df: pd.DataFrame,
    *,
    label_col: str = "Prognosis",
    # XGBoost params
    n_estimators: int = 400,
    max_depth: int = 6,
    learning_rate: float = 0.05,
    subsample: float = 0.8,
    colsample_bytree: float = 0.8,
    reg_lambda: float = 1.0,
    reg_alpha: float = 0.0,
    random_state: int = 0,
    n_jobs: int = -1,
    # SHAP speed knob (rows only; ALL features are still ranked)
    shap_sample_size: int = 2000,
) -> pd.DataFrame:
    """
    Train XGBoost, compute SHAP via XGBoost's native TreeSHAP (pred_contribs=True),
    and return a pandas DataFrame with columns:
      - 'Feature': feature name
      - 'Importance': mean |SHAP| across samples (and classes if multiclass)
    Ordered best → worst by SHAP, ties broken by XGBoost gain.

    Assumes:
      - df[label_col] is already encoded (ints 0..K-1)
      - feature columns are numeric
    """
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

    # Choose objective
    if len(classes) == 2:
        objective, num_class, eval_metric = "binary:logistic", None, "logloss"
    else:
        objective, num_class, eval_metric = "multi:softprob", len(classes), "mlogloss"

    # Fit with the DataFrame so feature names are preserved
    model = XGBClassifier(
        objective=objective,
        num_class=num_class,
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        reg_lambda=reg_lambda,
        reg_alpha=reg_alpha,
        random_state=random_state,
        n_jobs=n_jobs,
        eval_metric=eval_metric,
        tree_method="hist",
        verbosity=0,
    )
    model.fit(X, y)

    # Optional row subsample for SHAP speed
    if shap_sample_size is not None and X.shape[0] > shap_sample_size:
        rng = np.random.RandomState(random_state)
        idx = rng.choice(X.shape[0], shap_sample_size, replace=False)
        X_shap = X.iloc[idx, :]
    else:
        X_shap = X

    # ---- Compute SHAP via XGBoost's native TreeSHAP ----
    booster = model.get_booster()
    dmat = DMatrix(X_shap.values, feature_names=X.columns.tolist())
    contribs = booster.predict(dmat, pred_contribs=True)
    contribs = np.asarray(contribs)

    # Drop the last column = bias/base value and aggregate
    if contribs.ndim == 2:
        # (n_samples, n_features + 1)
        shap_vals = contribs[:, :-1]
        mean_abs_shap = np.mean(np.abs(shap_vals), axis=0)
    elif contribs.ndim == 3:
        # (n_samples, n_classes, n_features + 1)
        shap_vals = contribs[..., :-1]
        mean_abs_shap = np.mean(np.abs(shap_vals), axis=(0, 1))
    else:
        raise RuntimeError(f"Unexpected pred_contribs shape: {contribs.shape}")

    if mean_abs_shap.shape[0] != X.shape[1]:
        raise RuntimeError(
            f"SHAP per-feature length mismatch: got {mean_abs_shap.shape[0]}, expected {X.shape[1]}"
        )

    # Gain vector aligned to columns (0 for features never used in splits)
    fscore_gain = booster.get_score(importance_type="gain")  # dict: {name: gain}
    xgb_names = booster.feature_names or [f"f{i}" for i in range(X.shape[1])]
    if xgb_names == list(X.columns):
        name_to_idx = {name: i for i, name in enumerate(X.columns)}
    else:
        name_to_idx = {f"f{i}": i for i in range(X.shape[1])}

    gain_vec = np.zeros(X.shape[1], dtype=float)
    for name, g in fscore_gain.items():
        i = name_to_idx.get(name)
        if i is not None and 0 <= i < X.shape[1]:
            gain_vec[i] = float(g)

    # Strict order: primary SHAP (desc), secondary gain (desc)
    order = np.lexsort((-gain_vec, -mean_abs_shap))

    # Return DF with the exact same order
    return pd.DataFrame(
        {"Feature": X.columns[order].tolist(), "Importance": mean_abs_shap[order]}
    )
