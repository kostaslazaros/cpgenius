from enum import Enum
from typing import Any

from pydantic import BaseModel


class Algorithm(str, Enum):
    ANOVA_TEST = "anova_ftest"
    DUMMY_CLASSIFIER = "dummy_classifier"
    GARSEN_OLDEN_MLP = "garsen_olden_mlp"
    LASSO_LRC = "lasso_lrc"
    RANDOM_FOREST = "random_forest"
    RFE_SVM = "rfe_svm"
    RIDGE_L2 = "ridge_l2"
    SHAP_XGBOOST = "shap_xgboost"
    # Add new algorithms here as needed


class CSVUploadResponse(BaseModel):
    task_id: str
    sha1_hash: str
    message: str
    filename: str
    file_size: int


class PrognosisValuesResponse(BaseModel):
    sha1_hash: str
    filename: str
    unique_values: list[str]
    total_rows: int
    total_columns: int
    prognosis_column_found: bool
    message: str


class AlgorithmRequest(BaseModel):
    sha1_hash: str
    selected_prognosis_values: list[str]
    algorithm: Algorithm


class AlgorithmResponse(BaseModel):
    task_id: str
    sha1_hash: str
    algorithm: str
    selected_values: list[str]
    message: str


class DMPRequest(BaseModel):
    sha1_hash: str
    selected_prognosis_values: list[str]
    delta_beta: float = 0.4
    p_value: float = 0.05


class DMPResponse(BaseModel):
    task_id: str
    sha1_hash: str
    selected_values: list[str]
    message: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: dict[str, Any] = None
    error: str = None


class FileUploadResponse(BaseModel):
    task_id: str
    sha1_hash: str
    message: str
    file_count: int


class FileProcessingStatus(BaseModel):
    task_id: str
    status: str
    result: dict[str, Any] = None
    error: str = None


class Job(BaseModel):
    id: int
    algorithm: str
    params: dict[str, Any] = None
