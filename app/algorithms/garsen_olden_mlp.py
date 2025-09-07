import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.neural_network import MLPClassifier


def _connection_weights_importance(mlp) -> np.ndarray:
    """
    Olden/Garson-style importance for scikit-learn MLP:
    Propagate absolute output influence back to inputs through |W| products.
    Works for any number of hidden layers.
    """
    coefs = getattr(mlp, "coefs_", None)
    if not coefs:
        return None

    # Final layer: aggregate absolute influence across outputs
    last = coefs[-1]
    if last.ndim == 2:  # (n_hidden_last, n_outputs)
        downstream = np.sum(np.abs(last), axis=1)
    else:  # unlikely, but handle safety
        downstream = np.abs(last).ravel()

    # Backpropagate influence through hidden layers (excluding input layer)
    for W in reversed(coefs[1:-1]):
        downstream = np.abs(W) @ downstream  # shape: (n_prev,)

    # Input layer weights (n_features, n_hidden1)
    W_in = np.abs(coefs[0])
    # Importance of input i is sum over hidden of |W_in[i,h]| * downstream[h]
    importance = (W_in * downstream.reshape(1, -1)).sum(axis=1)
    return importance


def garsen_olden_mlp(
    df: pd.DataFrame,
    *,
    label_col: str = "Prognosis",
    # MLP hyperparams
    hidden_layer_sizes=(128,),
    activation="relu",
    alpha: float = 1e-4,
    learning_rate_init: float = 1e-3,
    max_iter: int = 300,
    early_stopping: bool = False,  # keep False to avoid internal val split
    # Training/data knobs
    upsample_classes: bool = True,  # simple upsample to the majority class count
    n_models: int = 5,  # average importance across this many seeds for stability
    random_state: int = 42,
    # Output
    csv_path: str = "ranked_features_olden_mlp.csv",
) -> pd.DataFrame:
    """
    Fits one or more MLPs on the FULL dataset (no split/CV, no scaling),
    computes Garson/Olden connection-weights importance, averages across runs,
    and returns a DataFrame with a single column 'feature' ranked most→least important.
    Also saves the CSV to `csv_path`.
    """
    if label_col not in df.columns:
        raise ValueError(f"Label column '{label_col}' not found.")

    y = df[label_col].to_numpy()
    X = df.drop(columns=[label_col])

    # Checks
    if not np.issubdtype(y.dtype, np.number):
        raise ValueError(f"'{label_col}' must be numeric/encoded already.")
    nonnum = [c for c in X.columns if not is_numeric_dtype(X[c])]
    if nonnum:
        raise ValueError(f"Non-numeric feature columns found: {nonnum}.")
    classes, counts = np.unique(y, return_counts=True)
    if len(classes) < 2:
        raise ValueError("Need at least two classes in the target.")

    # Optional upsampling on the FULL dataset (still a single fit per model)
    X_use, y_use = X, y
    if upsample_classes and len(classes) > 1:
        rng = np.random.default_rng(random_state)
        max_count = counts.max()
        idx_all = []
        for c in classes:
            idx_c = np.where(y == c)[0]
            need = max_count - len(idx_c)
            if need > 0:
                add = rng.choice(idx_c, size=need, replace=True)
                idx_all.append(np.concatenate([idx_c, add]))
            else:
                idx_all.append(idx_c)
        train_idx = np.concatenate(idx_all)
        rng.shuffle(train_idx)
        X_use = X.iloc[train_idx, :]
        y_use = y[train_idx]

    # Fit n_models times with different seeds; average importances
    rng_master = np.random.default_rng(random_state)
    imp_accum = np.zeros(X_use.shape[1], dtype=float)
    valid_runs = 0

    for _ in range(max(1, n_models)):
        seed = int(rng_master.integers(0, 2**31 - 1))
        mlp = MLPClassifier(
            hidden_layer_sizes=hidden_layer_sizes,
            activation=activation,
            alpha=alpha,
            learning_rate_init=learning_rate_init,
            solver="adam",
            max_iter=max_iter,
            early_stopping=early_stopping,  # keep False to avoid internal val split
            random_state=seed,
        )
        mlp.fit(X_use.values, y_use)
        imp = _connection_weights_importance(mlp)
        if imp is not None and np.isfinite(imp).all():
            imp_accum += imp
            valid_runs += 1

    if valid_runs == 0:
        raise RuntimeError("Failed to compute importances from MLP weights.")

    importances = imp_accum / valid_runs
    # Break ties by feature name for deterministic ordering
    feats = np.array(X_use.columns)
    order = np.lexsort((feats, -importances))
    ranked = pd.DataFrame({"Feature": feats[order], "Importance": importances[order]})
    return ranked
