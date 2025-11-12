# Q&A

<p align="justify">
<b>1. What is CpGene and what kind of data does it analyze?</b><br>
CpGene is a web application designed for the analysis of DNA methylation array data, supporting Illumina 450K, EPIC, and EPICv2 platforms. It processes raw <code>.idat</code> files and CSV data, performing automated preprocessing, normalization, quality control, feature selection, and gene enrichment analysis. The platform provides users—from early-career researchers to experienced bioinformaticians—with a complete and interactive environment for identifying epigenetic biomarkers and interpreting their biological significance.
</p>

---

<p align="justify">
<b>2. How is CpGene architecturally structured?</b><br>
CpGene follows a modern microservices architecture built with FastAPI, Celery, Redis, and Docker. The FastAPI layer manages the REST API and user interaction, Celery handles asynchronous task execution, Redis acts as the message broker, and Docker ensures containerized processing for R-based components. This modular design supports scalability, efficient job scheduling, and seamless integration between Python-based and R-based workflows.
</p>

---

<p align="justify">
<b>3. What happens when a user uploads .idat files?</b><br>
When users upload IDAT bundles through the web interface, CpGene computes a SHA-1 hash for file integrity verification and to prevent duplicate analyses. The files are stored under a structured directory (<code>uploads/{sha1_hash}/in/</code>), and Celery automatically schedules preprocessing tasks. These tasks invoke the R–MinFi container, which performs background correction, normalization, probe filtering, and quality control visualizations. The processed results, including normalized β-values and QC figures, are stored and made available for download as PNG or CSV files.
</p>

---

<p align="justify">
<b>4. Which preprocessing and normalization methods are implemented?</b><br>
CpGene uses the <i>MinFi</i> R package to handle preprocessing and normalization. The workflow includes detection p-value filtering (&gt; 0.01), background correction via the NOOB method, PCA-based adjustment for batch effects, and exclusion of low-quality or cross-reactive probes. It also filters out hemi-methylated CpG sites (β-values between 0.3–0.6) to ensure clarity between hypo- and hypermethylation states. The outputs include quality control plots for probe detection, bisulfite conversion efficiency, and normalized β-value distributions.
</p>

---

<p align="justify">
<b>5. What analytical approaches are available for biomarker discovery?</b><br>
CpGene provides two main analytical paths: (1) Differential Methylation Point (DMP) Analysis using the <i>limma</i> R package, which identifies CpG sites with significant methylation differences between two user-defined conditions; and (2) AI-based Feature Ranking, employing several machine learning algorithms (e.g., LASSO Logistic Regression, SHAP-XGBoost, Random Forest, RFE-SVM, Ridge-L2, and Garson-Olden MLP) for multi-class or binary classification tasks. These models help uncover CpG sites most relevant for class separation or prognostic prediction.
</p>

---

<p align="justify">
<b>6. How does CpGene visualize analysis results?</b><br>
CpGene generates high-resolution (300 dpi) visual outputs to help users interpret results. During preprocessing, it produces bar, dot, scatter, and density plots for QC assessment. For DMP analysis, volcano plots highlight hypermethylated and hypomethylated CpG sites. For AI-based feature selection, PCA scatter plots visualize sample clustering before and after ranking, demonstrating improved class separability. All visualizations are downloadable and dynamically rendered in the web interface.
</p>

---

<p align="justify">
<b>7. How are selected CpG sites mapped to genes and interpreted biologically?</b><br>
After DMP analysis or feature ranking, CpGene automatically maps CpG identifiers to their corresponding gene symbols using Illumina manifest annotations (for 450K, EPIC, or EPICv2 arrays). The mapped genes are then subjected to enrichment analysis via the Enrichr API, which identifies significantly enriched pathways or biological terms from databases like KEGG, Reactome, and WikiPathways. The results are displayed interactively as bar plots ranked by p-value or enrichment score.
</p>

---

<p align="justify">
<b>8. What technologies power the web interface and backend communication?</b><br>
The frontend is developed with HTML5, JavaScript, and Tailwind CSS, featuring drag-and-drop uploads, responsive layout, and real-time image galleries. It communicates with the backend via FastAPI endpoints, which expose routes for file upload, image retrieval, and ZIP downloads. Task orchestration is achieved through Celery with Redis, enabling non-blocking execution of heavy analyses, while Docker containers encapsulate the R environments for MinFi and limma, ensuring reproducibility and isolation.
</p>

---

<p align="justify">
<b>9. What measures ensure scalability, performance, and data integrity?</b><br>
CpGene employs SHA-1 hashing to ensure data integrity and detect previously processed bundles. Asynchronous Celery tasks allow parallel execution, while multiple workers can be deployed for scalability. Redis provides efficient message queuing and result management. Each analysis is stored under unique directories, and results are returned via secure API routes. This combination of distributed processing and data hashing ensures both reliability and performance under high computational loads.
</p>

---

<p align="justify">
<b>10. How can developers and researchers extend or deploy CpGene?</b><br>
The system can be launched locally using Docker Compose and <code>uv</code> for dependency management. Developers start Redis, run Celery workers, and launch the FastAPI server on port 8001. The open-source codebase on GitHub (<a href="https://github.com/kostaslazaros/cpgenius">https://github.com/kostaslazaros/cpgenius</a>) allows customization—such as adding new AI models, modifying preprocessing parameters, or integrating additional enrichment databases. Built on modular Python and R components, CpGene is easily extensible and deployable across local or cloud-based environments.
</p>
