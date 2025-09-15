from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import RFE, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC


class Notify(ABC):
    @abstractmethod
    def info(self, message: str):
        self(message)

    @abstractmethod
    def warning(self, message: str):
        self(message)

    @abstractmethod
    def error(self, message: str):
        self(message)


class NotifyCeleryTask(Notify):
    def __init__(self, notifier):
        self.notifier = notifier

    def info(self, message: str):
        if self.notifier:
            self.notifier.update_state(
                state="PROCESSING", meta={"status": message, "progress": 50}
            )

    def warning(self, message: str):
        if self.notifier:
            self.notifier.update_state(
                state="PROCESSING", meta={"status": message, "progress": 50}
            )

    def error(self, message: str):
        if self.notifier:
            self.notifier.update_state(
                state="PROCESSING", meta={"status": message, "progress": 50}
            )


class NotifyPrint(Notify):
    def info(self, message: str):
        self(message)

    def warning(self, message: str):
        self(message)

    def error(self, message: str):
        self(message)


def csv2df(csv_path: str, notify: Notify) -> pd.DataFrame:
    """Read CSV into DataFrame, trying utf-8 then latin-1 if needed.

    Raises ValueError if file is empty or has no valid data.
    """
    notify.info("Reading CSV file...")
    try:
        df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines="skip")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="latin-1", on_bad_lines="skip")
    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty or has no valid data")
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {str(e)}")

    if df.empty:
        raise ValueError("CSV file contains no data")

    return df


def xy_from_df(df: pd.DataFrame, label_col: str, notify: Notify):
    """
    Splits DataFrame into feature matrix X and target vector y.

    Assumes:
      - df[label_col] is ALREADY encoded (e.g., ints 0..K-1),
      - feature columns are numeric (e.g., 0..1).
    Returns:
      X: pd.DataFrame of features
      y: pd.Series of target
    """
    notify.info("Preparing data...")
    if label_col not in df.columns:
        raise ValueError(f"Label column '{label_col}' not found.")

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

    classes = np.unique(y)

    if len(classes) < 2:
        raise ValueError("Need at least two classes in the target.")

    return X, y, classes


def xy_anova_ftest(
    X: pd.DataFrame, y: pd.Series, notify: Notify = NotifyPrint()
) -> pd.DataFrame:
    notify.info("Performing ANOVA F-test...")
    F, p = f_classif(X.values, y)
    # Clean up edge cases (constant features, etc.)
    F = np.nan_to_num(F, nan=0.0, posinf=0.0, neginf=0.0)
    p = np.nan_to_num(p, nan=1.0, posinf=1.0, neginf=1.0)

    feats = np.array(X.columns)

    # Strict order: primary = F desc, secondary = p asc, tertiary = name asc
    order_idx = np.lexsort((feats, p, -F))
    return pd.DataFrame({"Feature": feats[order_idx], "Importance": F[order_idx]})


def xy_lasso_lrc(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    C: float = 0.5,
    max_iter: int = 8000,
    tol: float = 1e-3,
    class_weight: str = "balanced",
    random_state: int = 0,
    notify: Notify = NotifyPrint(),
):
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
    notify.info("Fitting Lasso Logistic Regression...")
    clf.fit(X.values, y)

    W = clf.coef_
    coef_score = np.abs(W) if W.ndim == 1 else np.linalg.norm(W, axis=0)

    Xv = X.values.astype(float)
    n = Xv.shape[0]
    Xc = Xv - Xv.mean(axis=0, keepdims=True)
    Xs = Xv.std(axis=0, ddof=1, keepdims=True)
    Xs[Xs == 0] = 1.0

    classes = np.unique(y)

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


def xy_random_forest_varimp(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    n_estimators: int = 300,
    max_depth: int = None,
    max_features="sqrt",  # good default for classification
    min_samples_leaf: int = 1,
    bootstrap: bool = True,
    max_samples=None,  # e.g., 0.5–0.8 to speed up on large datasets
    random_state: int = 0,
    n_jobs: int = -1,
    notify: Notify = NotifyPrint(),
) -> pd.DataFrame:
    """
    Rank ALL features (best → worst) using RandomForest variable importance.

    Assumes:
      - df[label_col] is ALREADY encoded (e.g., ints 0..K-1),
      - feature columns are numeric (e.g., 0..1).

    Returns:
      pd.DataFrame: single column 'Feature' ordered best → worst by importance.
    """
    notify.info("Fitting Random Forest...")
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


def xy_rfe_svm(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    C: float = 0.1,
    step: float = 0.99,
    tol: float = 5e-2,
    random_state: int = 0,
    max_iter: int = 5000,
    loss: str = "hinge",
    class_weight=None,
    notify: Notify = NotifyPrint(),
) -> pd.DataFrame:
    notify.info("Fitting RFE + Linear SVM...")
    X = X.to_numpy(dtype=np.float32, copy=False)
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
        rfe.ranking_, index=X.columns, name="RFE_rank"
    ).sort_values()  # 1 = best
    ordered_features = ranks.index.tolist()

    return pd.DataFrame(
        {"Feature": ordered_features, "Importance": ranks[ordered_features].values},
        index=range(len(ordered_features)),
    )


def workflow(
    csv_dataset,
    algorithm: callable,
    notify: Notify = NotifyPrint(),
    label_col: str = "Prognosis",
):
    df = csv2df(csv_dataset, notify=notify)
    X, y = xy_from_df(df, label_col=label_col, notify=notify)
    result = algorithm(X, y, notify=notify)
    return result
