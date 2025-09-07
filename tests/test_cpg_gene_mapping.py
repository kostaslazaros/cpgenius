from pathlib import Path

import pandas as pd

from app.cpg2gene.cpg_gene_mapping import (
    build_gene_names_csv,
    clean_gene_names_csv,
    guess_type,
)

current_dir = Path(__file__).parent.resolve()


def test_build_gene_names_csv():
    # build_gene_names_csv(
    #     array_type="450k",
    #     input="./tests/test_data/test_input_450k.csv",
    #     output_dir="./tests/test_data/",
    # )
    # build_gene_names_csv(
    #     array_type="epic",
    #     input="./tests/test_data/test_input_epic.csv",
    #     output_dir="./tests/test_data/",
    # )

    out_file = build_gene_names_csv(
        array_type="epicv2",
        input=current_dir / "test_data" / "ranked_features_lasso_logistic.csv",
        output_dir=current_dir / "test_data",
    )
    Path(out_file).unlink()


def test_build_gene_names_top_feats_csv():
    # build_gene_names_csv(
    #     array_type="450k",
    #     input="./tests/test_data/test_input_450k.csv",
    #     output_dir="./tests/test_data/",
    # )
    # build_gene_names_csv(
    #     array_type="epic",
    #     input="./tests/test_data/test_input_epic.csv",
    #     output_dir="./tests/test_data/",
    # )

    out_file = build_gene_names_csv(
        array_type="epicv2",
        input=current_dir / "test_data" / "ranked_features_lasso_logistic.csv",
        output_dir=current_dir / "test_data",
        fno=100,
    )

    test_df = pd.read_csv(out_file)
    # print(test_df)
    assert test_df.shape[0] == 100

    Path(out_file).unlink()


def test_clean_gene_names_csv():
    input_csv = build_gene_names_csv(
        array_type="epicv2",
        input=current_dir / "test_data" / "ranked_features_lasso_logistic.csv",
        output_dir=current_dir / "test_data",
    )
    output_csv = current_dir / "test_data" / "epicv2_mal.csv"

    out_file = clean_gene_names_csv(
        input_csv=str(input_csv), output_csv=str(output_csv)
    )

    test_df = pd.read_csv(out_file)
    assert test_df["GeneName"].isna().sum() == 0

    Path(input_csv).unlink()
    Path(output_csv).unlink()


def test_check_type():
    feature_df = pd.read_csv(
        current_dir / "test_data" / "ranked_features_lasso_logistic.csv"
    )
    guess_type(feature_df)
