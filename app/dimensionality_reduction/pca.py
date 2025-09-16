import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA


def pca_plot(
    df: pd.DataFrame,
    conditions: list[str] | None = None,
    fs_algorithm_name: str | None = None,
    selected_features: list[str] | None = None,
    n_components: int = 2,
):
    if conditions:
        df = df[df["Prognosis"].isin(conditions)]

    # 1) Pick feature columns
    if selected_features is None:
        feat_cols = [c for c in df.columns if c != "Prognosis"]
    else:
        feat_cols = [
            c for c in selected_features if c in df.columns and c != "Prognosis"
        ]

    # 2) Full vs Selected feature matrices
    X_full = df.drop(columns=["Prognosis"])
    X_selected = df[feat_cols]

    full_feature_number = X_full.shape[1]
    selected_feature_number = X_selected.shape[1]

    # 3) PCA
    pca_full = PCA(n_components=n_components, random_state=0)
    pca_sel = PCA(n_components=n_components, random_state=0)

    PC_full = pca_full.fit_transform(X_full)
    PC_selected = pca_sel.fit_transform(X_selected)

    # 4) Build PCA dataframe
    principalDf_2d_full = pd.DataFrame(PC_full[:, :2], columns=["PC 1", "PC 2"])
    principalDf_2d_full["Prognosis"] = df["Prognosis"].values

    principalDf_2d_sel = pd.DataFrame(PC_selected[:, :2], columns=["PC 1", "PC 2"])
    principalDf_2d_sel["Prognosis"] = df["Prognosis"].values

    # 5) Colors: consistent across subplots
    labels = df["Prognosis"].unique()
    colors = sns.color_palette("tab20", n_colors=len(labels))
    color_map = dict(zip(labels, colors))

    # 6) Plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharex=True, sharey=True)

    # 🔹 Set figure and axes background
    fig.patch.set_facecolor("#f8fafc")
    for ax in axes:
        ax.set_facecolor("#f8fafc")

    # Left: full features
    for label in labels:
        mask = principalDf_2d_full["Prognosis"] == label
        axes[0].scatter(
            principalDf_2d_full.loc[mask, "PC 1"],
            principalDf_2d_full.loc[mask, "PC 2"],
            c=[color_map[label]],
            s=50,
            edgecolors="gray",
            alpha=0.77,
            label=label,
        )
    axes[0].set_title(f"PCA (Full: {full_feature_number} features)")
    axes[0].set_xlabel("PC 1")
    axes[0].set_ylabel("PC 2")

    # Right: selected features
    for label in labels:
        mask = principalDf_2d_sel["Prognosis"] == label
        axes[1].scatter(
            principalDf_2d_sel.loc[mask, "PC 1"],
            principalDf_2d_sel.loc[mask, "PC 2"],
            c=[color_map[label]],
            s=50,
            edgecolors="gray",
            alpha=0.77,
            label=label,
        )
    if fs_algorithm_name:
        axes[1].set_title(
            f"PCA (Selected: {selected_feature_number} features, {fs_algorithm_name})"
        )
    else:
        axes[1].set_title(f"PCA (Selected: {selected_feature_number} features)")
    axes[1].set_xlabel("PC 1")
    axes[1].set_ylabel("PC 2")

    # Common legend outside plot
    handles, labels = axes[0].get_legend_handles_labels()
    legend = fig.legend(
        handles,
        labels,
        title="Prognosis",
        loc="lower center",
        ncol=len(labels),
        frameon=True,
    )
    # 🔹 Match legend background
    legend.get_frame().set_facecolor("#f8fafc")
    legend.get_frame().set_edgecolor("none")

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    return fig
