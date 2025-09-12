from pathlib import Path

import pandas as pd

from app.dimensionality_reduction.pca import pca_plot

PATH = Path(__file__).parent.parent / "test_data"


def test_pca_plot():
    path = PATH / "bval_data.csv"

    df = pd.read_csv(path)
    features = [c for c in df.columns if c != "Prognosis"]
    top_feats = features[:300]

    pca_plot(
        df,
        conditions=["Indolent", "Normal", "High_grade", "AVPC"],
        features=top_feats,
        output_path=".",
        save_png=False,
    )
