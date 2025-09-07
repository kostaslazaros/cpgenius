from typing import Callable, Dict

from app.algorithms.anova_ftest import anova_ftest
from app.algorithms.dummy_classifier import dummy_classifier
from app.algorithms.garsen_olden_mlp import garsen_olden_mlp
from app.algorithms.lasso_logistic_regression import lasso_lrc
from app.algorithms.random_forest_varimp import random_forest_varimp
from app.algorithms.rfe_svm import rfe_svm
from app.algorithms.ridge_l2 import ridge_l2
from app.algorithms.shap_xgboost import shap_xgboost
from app.schemas import Algorithm

# Canonical registry keyed by the Algorithm enum
ALGORITHM_REGISTRY: Dict[Algorithm, Callable] = {
    Algorithm.ANOVA_TEST: anova_ftest,
    Algorithm.DUMMY_CLASSIFIER: dummy_classifier,
    Algorithm.GARSEN_OLDEN_MLP: garsen_olden_mlp,
    Algorithm.LASSO_LRC: lasso_lrc,
    Algorithm.RANDOM_FOREST: random_forest_varimp,
    Algorithm.RFE_SVM: rfe_svm,
    Algorithm.RIDGE_L2: ridge_l2,
    Algorithm.SHAP_XGBOOST: shap_xgboost,
    # Add new algorithms here as needed
}
# Backwards-compatible mapping keyed by the string values (eg. used by some callers)
ALGORITHMS: Dict[str, Callable] = {
    alg.value: fn for alg, fn in ALGORITHM_REGISTRY.items()
}


def get_algorithms():
    """Get list of available feature selection algorithms."""
    algorithms = []
    for algorithm in Algorithm:
        algorithms.append(
            {
                "id": algorithm.value,
                "name": algorithm.value.replace("_", " ").title(),
                "description": f"{algorithm.value.replace('_', ' ').title()} feature selection algorithm",
            }
        )
    return {"algorithms": algorithms}
