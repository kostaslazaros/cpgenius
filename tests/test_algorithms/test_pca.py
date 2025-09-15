from pathlib import Path

import pandas as pd

from app.dimensionality_reduction.pca import pca_plot

PATH = Path(__file__).parent.parent / "test_data"


def test_pca_plot():
    path = PATH / "bval_data.csv"

    df = pd.read_csv(path)
    features = [c for c in df.columns if c != "Prognosis"]
    top_feats = features[:200]

    fig = pca_plot(
        df,
        conditions=["Indolent", "Normal", "High_grade", "AVPC"],
        selected_features=top_feats,
        fs_algorithm_name="ANOVA F-test",
    )

    # fig.savefig("test_pca_plot.png", dpi=300, bbox_inches="tight")
    assert fig is not None
