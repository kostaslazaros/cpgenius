# Overview

<div style="text-align: justify;">

CpGene is a web application designed to simplify and accelerate the analysis of DNA methylation array data. It provides an integrated, user-friendly environment that supports Illumina 450K, EPIC, and EPICv2 platforms, allowing researchers to perform preprocessing/quality control, biomarker identification, and feature enrichment all in one place. At its core, CpGene streamlines epigenetic biomarker discovery by combining traditional differential methylation point (DMP) analysis with machine learning–based feature selection. Users can explore CpG sites and genes of biological or clinical significance through clear visualizations such as PCA plots, volcano plots, and enrichment charts.

</div>

<br>

![](/static/doc_images/CpGene_Diagram_v23.png)

<div style="text-align: justify;">

Overview of the CpGene workflow. The pipeline consists of three main stages: Beta Value Creator, Biomarker Identification, and Enrichment Analysis. Starting from Illumina IDAT files, CpGene performs preprocessing and quality control to generate normalized beta values and corresponding QC visualizations. These values are used for biomarker discovery through either machine learning–based feature selection or differential methylation point (DMP) analysis. During feature selection, sample distributions are visualized via principal component analysis (PCA) plots generated both before and after the selection process, whereas in DMP analysis, methylation differences across CpG sites are illustrated using volcano plots. Identified CpG sites are subsequently mapped to their corresponding genes. The final stage conducts pathway and term enrichment through Enrichr-based functional annotation, facilitating biological interpretation and the identification of enriched molecular pathways of potential clinical relevance

</div>

<br>

<div style="text-align: justify;">

Preprocessing and quality control are performed using the robust R-based package minfi, ensuring reliable data normalization and filtering. The integrated AI-based CpG ranking engine, built on scikit-learn, allows users to prioritize features under different modeling assumptions, while gene set enrichment analysis via Enrichr provides biological interpretation of the identified signatures. CpGene is intended for a wide range of users offering a fast, accessible, and transparent solution for analyzing complex methylation datasets without requiring coding skills. By unifying all essential steps into a cohesive interface, CpGene supports the discovery of meaningful epigenetic signatures that advance our understanding of disease mechanisms and potential biomarkers.

</div>

---

**Source Code:** [https://github.com/kostaslazaros/cpgenius](https://github.com/kostaslazaros/cpgenius)  
**Contact:** [lakonstant@ionio.gr](mailto:lakonstant@ionio.gr)
