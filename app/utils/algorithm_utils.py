import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from app.config import cnf

TAG = cnf.prognosis_column_name


def fs_wrapper(
    *,
    algorithm,
    csv_path,
    selected_prognosis: list = None,
    parent=None,
) -> dict:
    if parent:
        parent.update_state(
            state="PROCESSING", meta={"status": "Reading CSV file...", "progress": 1}
        )
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

    if TAG not in df.columns:
        raise ValueError(f"CSV file must contain a '{TAG}' column")

    if parent:
        parent.update_state(
            state="PROCESSING", meta={"status": "Preparing data...", "progress": 10}
        )
    all_prognosis = list(df[TAG].unique())
    all_prognosis.sort()

    # Filter data for selected prognosis values
    if selected_prognosis:
        df = df[df[TAG].isin(selected_prognosis)].copy()
    else:
        selected_prognosis = all_prognosis

    if parent:
        parent.update_state(
            state="PROCESSING", meta={"status": "Encoding labels...", "progress": 20}
        )

    # Prepare data for algorithm (encode Prognosis if needed)
    df_for_algorithm = df.copy()

    label_encoder = LabelEncoder()
    df_for_algorithm[TAG] = label_encoder.fit_transform(df_for_algorithm[TAG])

    # Only keep numeric columns for feature ranking
    numeric_columns = df_for_algorithm.select_dtypes(
        include=[np.number]
    ).columns.tolist()
    if TAG in numeric_columns:
        numeric_columns.remove(TAG)

    # Keep only Prognosis + numeric feature columns
    df_for_algorithm = df_for_algorithm[[TAG] + numeric_columns]

    if len(numeric_columns) == 0:
        raise ValueError("No numeric columns found for feature ranking")

    # Run the feature ranking algorithm
    try:
        if parent:
            parent.update_state(
                state="PROCESSING",
                meta={"status": "Running algorithm...", "progress": 30},
            )

        feature_ranking = algorithm(df_for_algorithm)
    except Exception as e:
        raise ValueError(f"Error running {algorithm}: {str(e)}")

    return {
        "feature_ranking": feature_ranking,
        "df": df,
        "all_prognosis": all_prognosis,
        "selected_prognosis": selected_prognosis,
        "total_samples": len(df),
        "features_ranked": len(numeric_columns),
        "numeric_features_used": len(numeric_columns),
        "class_mapping": {
            str(i): str(class_name)
            for i, class_name in enumerate(label_encoder.classes_)
        },
    }
