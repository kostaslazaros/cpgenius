import pandas as pd
from pandas.api.types import is_numeric_dtype

# from app.schemas.task import Job

TAG_COL = "Prognosis"  # default label column name


def read_unique_categories_from_csv(
    csv_path: str, sep: str = ",", decimal: str = ".", case_sensitive: bool = True
) -> dict:
    """
    Reads a CSV and returns unique categories from the specified label column.
    If case_sensitive is False, categories are returned in lowercase.
    """
    df = pd.read_csv(csv_path, sep=sep, decimal=decimal)

    if TAG_COL not in df.columns:
        raise ValueError(
            f"Label column '{TAG_COL}' not found. Columns: {list(df.columns)}"
        )

    uniques = pd.unique(df[TAG_COL])

    if not case_sensitive:
        uniques = [str(u).lower() for u in uniques]

    lst_uniques = list(uniques)
    lst_uniques.sort()
    return lst_uniques


def extract_unique_tags(csv_path: str):
    col = pd.read_csv(
        csv_path, usecols=[TAG_COL], dtype={TAG_COL: "string"}, engine="c"
    )[TAG_COL]
    uns = pd.unique(col)
    return uns.tolist()


def prepare_prognosis_dataframe_from_csv(
    csv_path: str,
    ordered_categories: list = [],
    *,
    label_col: str = "Prognosis",
    sep: str = ",",
    decimal: str = ".",
    dropna_rows: bool = True,
    drop_duplicates: bool = False,
    ensure_label_last: bool = True,
    validate_numeric_features: bool = True,
    case_sensitive: bool = True,
    # job: Job = None,
) -> pd.DataFrame:
    """
    Reads CSV, optionally prompts user to choose and order categories for `label_col`,
    filters rows accordingly, encodes labels to 0..N-1 following that order,
    and returns ONE DataFrame. Mapping is stored in df.attrs['label_mapping'].
    """
    # if job is None create a dummy job
    # if job is None:
    #     job = Job(id=1, algorithm="", params=[])

    # job.job_logger.add_log(
    #     "We are inside helpers.py prepare_prognosis_dataframe_from_csv"
    # )
    # job.job_logger.add_log(f"Reading CSV to pandas DataFrame: {csv_path}")

    try:
        df = pd.read_csv(
            csv_path,
            sep=sep,
            decimal=decimal,
            encoding="utf-8",
            on_bad_lines="skip",  # Skip problematic lines instead of failing
        )
    except UnicodeDecodeError:
        # job.job_logger.add_log("UTF-8 encoding failed, trying latin-1...")
        df = pd.read_csv(
            csv_path, sep=sep, decimal=decimal, encoding="latin-1", on_bad_lines="skip"
        )
    except pd.errors.EmptyDataError:
        # job.job_logger.add_log("CSV file is empty or has no valid data")
        raise ValueError("CSV file is empty or has no valid data")
    except Exception as e:
        # job.job_logger.add_log(f"Error reading CSV: {str(e)}")
        raise ValueError(f"Could not read CSV file: {str(e)}")

    if df.empty:
        # job.job_logger.add_log("CSV file contains no data rows")
        raise ValueError("CSV file contains no data rows")

    # job.job_logger.duration_from_last(f"Successfully loaded DataFrame {df.shape}")

    # job.job_logger.add_log("check CSV columns")
    if label_col not in df.columns:
        # job.job_logger.add_log(
        #     f"Label column '{label_col}' not found. Columns: {list(df.columns)}"
        # )
        raise ValueError(
            f"Label column '{label_col}' not found. Columns: {list(df.columns)}"
        )

    # job.job_logger.duration_from_last("finished checking CSV columns")
    if drop_duplicates:
        # job.job_logger.add_log("Dropping duplicates")
        df = df.drop_duplicates()
        # job.job_logger.duration_from_last("finished dropping duplicates")

    # Discover unique categories in order of appearance
    # job.job_logger.add_log("Discovering unique categories")
    uniques = pd.unique(df[label_col])

    # job.job_logger.duration_from_last(f"Unique categories before filtering: {uniques}")
    # Now we have ordered_categories
    if not ordered_categories or not isinstance(ordered_categories, (list, tuple)):
        ordered_categories = [
            str(cat).lower() if not case_sensitive else str(cat) for cat in uniques
        ]
        ordered_categories.sort()

    # job.job_logger.duration_from_last(f"Ordered categories: {ordered_categories}")
    # Filter rows
    # job.job_logger.add_log("Filtering rows by ordered categories")
    df_filtered = df[df[label_col].isin(ordered_categories)].copy()
    if df_filtered.empty:
        # job.job_logger.add_log(
        #     "No rows left after filtering by the requested categories"
        # )
        raise ValueError("No rows left after filtering by the requested categories.")
    # job.job_logger.duration_from_last("finished filtering rows")

    # Verify all requested categories exist post-filter
    # job.job_logger.add_log("Verifying requested categories")
    present = set(pd.unique(df_filtered[label_col]))
    missing = [c for c in ordered_categories if c not in present]
    if missing:
        # job.job_logger.add_log(
        #     f"Requested categories not found after filtering: {missing}. "
        #     f"Available in CSV: {sorted(df[label_col].unique())}"
        # )
        raise ValueError(
            f"Requested categories not found after filtering: {missing}. "
            f"Available in CSV: {sorted(df[label_col].unique())}"
        )
    # job.job_logger.duration_from_last("finished verifying requested categories")
    # Encode strictly by provided order
    # job.job_logger.add_log("Encoding labels by provided order")
    label_mapping = {cat: i for i, cat in enumerate(ordered_categories)}
    df_filtered[label_col] = df_filtered[label_col].map(label_mapping).astype(int)

    # job.job_logger.duration_from_last("finished encoding labels")
    # This is very slow for large DataFrames

    if dropna_rows:
        # job.job_logger.add_log("Dropping NA rows")
        df_filtered = df_filtered.dropna(axis=0)
        # job.job_logger.duration_from_last("finished dropping NA rows")

    # job.job_logger.add_log("Validating numeric features")
    if validate_numeric_features:
        nonnum = [
            c
            for c in df_filtered.columns
            if c != label_col and not is_numeric_dtype(df_filtered[c])
        ]
        if nonnum:
            # job.job_logger.add_log(
            #     f"Non-numeric feature columns found: {nonnum}. "
            #     f"Encode/convert them before feature selection."
            # )
            raise ValueError(
                f"Non-numeric feature columns found: {nonnum}. "
                f"Encode/convert them before feature selection."
            )
    # job.job_logger.duration_from_last("finished validating numeric features")

    if ensure_label_last:
        # job.job_logger.add_log("Ensuring label column is last")
        cols = [c for c in df_filtered.columns if c != label_col] + [label_col]
        df_filtered = df_filtered.loc[:, cols]
        # job.job_logger.duration_from_last("finished ensuring label column is last")

    # Store mapping in metadata (return ONE object)
    df_filtered.attrs["label_mapping"] = label_mapping
    df_filtered.attrs["ordered_categories"] = list(ordered_categories)
    # job.job_logger.add_log("Returning filtered DataFrame")
    return df_filtered


async def read_big_file(save_path: str, file) -> pd.DataFrame:
    CHUNK_SIZE = 1024 * 1024 * 10  # 10MB chunks
    loops = 0
    total_bytes = 0
    await file.seek(0)

    with open(save_path, "wb") as buffer:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            buffer.write(chunk)
            loops += 1
            total_bytes += len(chunk)
            print(f"Chunk {loops} written ({len(chunk)} bytes)")

    print(f"File saved: {save_path} ({total_bytes} bytes)")

    # Validate file was written successfully
    if total_bytes == 0:
        raise ValueError("No data was written to file - uploaded file may be empty")
