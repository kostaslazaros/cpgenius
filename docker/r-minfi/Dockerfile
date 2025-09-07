FROM bioconductor/bioconductor_docker:3.19

LABEL maintainer="konlazaros@gmail.com"

# Install system dependencies often required by Bioc packages
RUN apt-get update && apt-get install -y \
    libxml2-dev \
    libssl-dev \
    libcurl4-openssl-dev \
    libxt-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Bioconductor packages
RUN R -e "BiocManager::install(c('minfi', 'minfiData', 'missMethyl', 'IlluminaHumanMethylationEPICv2manifest', 'IlluminaHumanMethylationEPICv2anno.20a1.hg38', 'limma'), ask=FALSE)"

# (Optional) validate that packages are consistent
RUN R -e "BiocManager::valid()"

RUN R -e "install.packages(c('devtools', 'ggplot2', 'ggrepel', 'glue'))"

RUN R -e "devtools::install_github('markgene/maxprobes')"

# Set default working directory
WORKDIR /workspace

RUN mkdir -p idat results

COPY  idat_preprocessor.R dmp_volcano_analysis.R .


CMD ["Rscript", "idat_preprocessor.R"]
