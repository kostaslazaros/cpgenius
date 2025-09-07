from pathlib import Path

import pandas as pd

from app.config import cnf


def build_gene_names_csv(
    *, array_type: str, input: str, output_dir: str, fno: int = 0
) -> str:
    assert array_type.lower() in ["450k", "epic", "epicv2"]

    input_file_name = Path(input).stem

    annotation_df = pd.read_pickle(cnf.pkl_files.get(array_type.lower()))

    features_df = pd.read_csv(
        input, usecols=["Feature"], dtype="string", keep_default_na=True
    )

    if fno > 0:
        features_df = features_df.iloc[:fno, :]

    # STRICT ORDER PRESERVATION: Keep the exact original order from input
    features = features_df["Feature"].dropna().astype(str).tolist()
    feature_set = set(features)
    assert len(feature_set) == len(features), "Input features contain duplicates!"

    result_df = annotation_df[annotation_df["CpG_site"].isin(feature_set)]

    # Reorder to match the order of features
    result_df = result_df.set_index("CpG_site").loc[features].reset_index()

    outfile = Path(output_dir) / f"{array_type}_{input_file_name}_mapped_genes.csv"
    result_df.to_csv(outfile, index=False)
    return str(outfile)


# def guess_type(feature_df: pd.DataFrame) -> str:
#     if "Feature" not in feature_df.columns:
#         raise ValueError("Input DataFrame must contain a 'Feature' column.")

#     if not pd.api.types.is_string_dtype(feature_df["Feature"]):
#         raise ValueError("The 'Feature' column must be of string type.")

#     feature_set = set(feature_df["Feature"].astype(str).tolist())
#     found = []

#     for selector, path in cnf.pkl_files.items():
#         annotation_df = pd.read_pickle(path)
#         selector_set = set(annotation_df["CpG_site"].astype(str).tolist())
#         if feature_set.issubset(selector_set):
#             print(f"Detected array type: {selector}")
#             found.append(selector)

#     if not found:
#         raise ValueError("No matching array type found.")

#     if len(found) > 1:
#         raise ValueError("Multiple matching array types found:", found)

#     return found[0]


def guess_illumina_array_type(columnset: set) -> list[str]:
    """Guess Illumina array type(s) based on provided set of CpG site IDs."""
    found = []

    for selector, path in cnf.pkl_files.items():
        annotation_df = pd.read_pickle(path)
        selector_set = set(annotation_df["CpG_site"].astype(str).tolist())

        if columnset.issubset(selector_set):
            # print(f"Detected array type: {selector}")
            found.append(selector)

    return found


def guess_illumina_array_type_pd(column_index: pd.Index) -> list[str]:
    """Most efficient - work with Index objects."""
    found = []
    column_set = set(column_index.astype(str))

    for annotator, path in cnf.pkl_files.items():
        annotation_df = pd.read_pickle(path)
        annotation_set = set(annotation_df["CpG_site"].astype(str).tolist())

        if column_set.issubset(annotation_set):
            found.append(annotator)

    return found


def build_gene_names_df(
    *, array_type: str, feature_df: pd.DataFrame, fno: int = 0
) -> pd.DataFrame:
    assert array_type.lower() in ["450k", "epic", "epicv2"]

    annotation_df = pd.read_pickle(cnf.pkl_files.get(array_type.lower()))
    if fno > 0:
        feature_df = feature_df.iloc[:fno, :]

    # STRICT ORDER PRESERVATION: Keep the exact original order from input
    features = feature_df["Feature"].astype(str).tolist()
    feature_set = set(features)

    assert len(feature_set) == len(features), "Input features contain duplicates!"

    result_df = annotation_df[annotation_df["CpG_site"].isin(feature_set)]

    # Reorder to match the order of features
    result_df = result_df.set_index("CpG_site").loc[features].reset_index()
    result_df = result_df.join(feature_df.drop(columns=["Feature"]))
    return result_df


def build_gene_names_using_csv(
    *, array_type: str, feature_csv_path: str, csv_with_genes_path: str, fno: int = 0
) -> pd.DataFrame:
    df = pd.read_csv(feature_csv_path)
    res = build_gene_names_df(array_type=array_type, feature_df=df, fno=fno)
    res.to_csv(csv_with_genes_path, index=False)


def clean_gene_names_csv(input_csv: str, output_csv: str) -> str:
    df = pd.read_csv(input_csv)
    clean_df = df.dropna(subset=["GeneName"], how="all").reset_index(drop=True)
    outfile = Path(output_csv)
    clean_df.to_csv(outfile, index=False)
    return str(outfile)
