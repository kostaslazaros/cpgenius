from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA


def pca_plot(
    df: pd.DataFrame,
    conditions: list[str] | None = None,
    features: list[str] | None = None,
    n_components: int = 2,
    output_path: str = "/output",
    save_png: bool = True,
):
    # print(f"dataframe head: {df.head()}")
    # print(f"unique conditions: {df['Prognosis'].unique()}")
    if conditions:
        df = df[df["Prognosis"].isin(conditions)]

    # 2) Pick feature columns
    if features is None:
        feat_cols = [c for c in df.columns if c != "Prognosis"]
    else:
        feat_cols = [c for c in features if c in df.columns and c != "Prognosis"]

    # 3) Keep only numeric columns (PCA requires numeric input)
    X = df[feat_cols].select_dtypes(include="number")
    feature_number = X.shape[1]

    # 4) PCA
    pca = PCA(n_components=n_components, random_state=0)
    PCs = pca.fit_transform(X)

    # 5) Build PCA dataframe
    principalDf_2d = pd.DataFrame(PCs[:, :2], columns=["PC 1", "PC 2"])
    principalDf_2d["Prognosis"] = df["Prognosis"].values

    # 6) Colors: as many as needed with seaborn
    labels = principalDf_2d["Prognosis"].unique()
    colors = sns.color_palette("tab20", n_colors=len(labels))

    plt.figure(figsize=(8, 6))
    for label, color in zip(labels, colors):
        mask = principalDf_2d["Prognosis"] == label
        plt.scatter(
            principalDf_2d.loc[mask, "PC 1"],
            principalDf_2d.loc[mask, "PC 2"],
            c=[color],
            s=50,
            edgecolors="gray",
            alpha=0.77,
            label=label,
        )

    plt.title(f"PCA 2D ({feature_number} features)")
    plt.xlabel("Principal Component 1")
    plt.ylabel("Principal Component 2")
    plt.legend()

    # Save at 300 dpi with feature count in filename
    Path(output_path).mkdir(parents=True, exist_ok=True)
    filename = f"{output_path}/pca_2d_{feature_number}_features.png"
    if save_png:
        plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.show()
