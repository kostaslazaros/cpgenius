library(glue)
library(limma)
library(ggplot2)
library(ggrepel)


dmp_volcano <- function(csv_path, condition1, condition2, delta_beta_thres, p_value_thres) {
  # Comparison Groups
  comp_vec <- c(condition1, condition2)
  
  # Read beta-values matrix from disk
  bvals <- read.csv(file=csv_path, 
                    header=TRUE, 
                    stringsAsFactors=TRUE)
  
  bvals <- bvals[bvals$Prognosis %in% comp_vec, , drop = FALSE]
  
  # this is the factor of interest
  prognosis <- factor(bvals$Prognosis)
  
  rownames(bvals) <- make.unique(as.character(bvals$Prognosis))
  bvals$Prognosis <- NULL
  bvals <- as.data.frame(t(bvals))
  
  # keep only numeric columns (ignores Prognosis automatically)
  bvals <- bvals[, vapply(bvals, is.numeric, logical(1L)), drop = FALSE]
  
  bvals <- as.matrix(bvals)
  design <- model.matrix(~0+prognosis)
  colnames(design) <- c(levels(prognosis))
  fit1 <- lmFit(bvals, design)
  
  # create a contrast matrix for specific comparisons
  contrast_str <- sprintf("%s-%s", comp_vec[1], comp_vec[2])
  contMatrix <- makeContrasts(contrasts = contrast_str, levels = design)
  
  # fit the contrasts
  fit2 <- contrasts.fit(fit1, contMatrix)
  fit2 <- eBayes(fit2)
  
  DMPs <- topTable(fit2, num=Inf, coef=1)
  DMPs <- DMPs[, c("logFC", "P.Value")]
  
  colnames(DMPs)[colnames(DMPs) == "logFC"] <- "deltaBeta"
  
  DMPs$neg_log10_pval <- -log10(DMPs$P.Value)
  
  # Biostatsquid theme
  theme_set(theme_classic(base_size = 20) +
                       theme(
                         axis.title.y = element_text(face = "bold", margin = margin(0,20,0,0), size = rel(1.1), color = 'black'),
                         axis.title.x = element_text(hjust = 0.5, face = "bold", margin = margin(20,0,0,0), size = rel(1.1), color = 'black'),
                         plot.title = element_text(hjust = 0.5)
                       ))
  
  DMPs$diffexpressed <- "NO"
  DMPs$diffexpressed[DMPs$deltaBeta >= delta_beta_thres & DMPs$P.Value <= p_value_thres ] <- "UP"
  DMPs$diffexpressed[DMPs$deltaBeta <= -delta_beta_thres & DMPs$P.Value <= p_value_thres] <- "DOWN"
  head(DMPs[order(DMPs$P.Value) & DMPs$diffexpressed == 'DOWN', ])
  
  
  top_downregulated <- DMPs[DMPs$diffexpressed == "DOWN", ][order(-DMPs$neg_log10_pval[DMPs$diffexpressed == "DOWN"], DMPs$deltaBeta[DMPs$diffexpressed == "DOWN"]), ][1:3,]
  
  top_upregulated <- DMPs[DMPs$diffexpressed == "UP", ][order(-DMPs$neg_log10_pval[DMPs$diffexpressed == "UP"], -DMPs$deltaBeta[DMPs$diffexpressed == "UP"]), ][1:3,]
  
  
  top_dmps_combined <- c(rownames(top_downregulated), rownames(top_upregulated))
  
  df_annotated <- DMPs[rownames(DMPs) %in% top_dmps_combined,]
  
  
  p <- ggplot(data=DMPs, aes(x=deltaBeta, y= -log10(P.Value), col=diffexpressed)) +
    geom_vline(xintercept=c(-delta_beta_thres, delta_beta_thres), col = "gray", linetype = 'dashed') +
    geom_hline(yintercept=-log10(p_value_thres), col = "gray", linetype = 'dashed') + 
    geom_point(size=2) + 
    scale_color_manual(values=c("#5ce65c", "grey", "#bb0c00"),
                                labels=c("Hypomethylated", "Not significant", "Hypermethylated")) +
    coord_cartesian(ylim=c(0, max(DMPs$neg_log10_pval)), xlim=c(min(DMPs$deltaBeta), max(DMPs$deltaBeta))) +
    labs(color='', x=expression("Delta Beta"), y=expression("-log"[10]*"p-value")) +
    scale_x_continuous(breaks=seq(min(DMPs$deltaBeta), 1, max(DMPs$deltaBeta))) +
    ggtitle(glue::glue("DMPs ({comp_vec[1]} vs {comp_vec[2]})"))
  
  # Adding labels with ggrepel for better visibility and avoiding overlaps
  p_labeled <- p + geom_label_repel(data=df_annotated, aes(label=rownames(df_annotated), x=deltaBeta, y= -log10(P.Value)),
                                             box.padding=0.35, point.padding = 0.5, 
                                             size=6, segment.color='grey50', show.legend=FALSE)
  
  ggsave(glue("./dmp_results/dmp_volcano_plot_{comp_vec[1]}_vs_{comp_vec[2]}.png"),
                  plot = p_labeled, width = 11, height = 6, units = "in", dpi = 300, bg = "white")
  
  DMPs <- subset(DMPs, diffexpressed %in% c("UP", "DOWN"))
  DMPs <- cbind(Feature = rownames(DMPs), DMPs)
  
  write.csv(DMPs, glue("./dmp_results/dmps_{comp_vec[1]}_vs_{comp_vec[2]}.csv"), row.names = FALSE)
}


dmp_volcano(csv_path = "./data/csv/bval_data.csv",
            condition1 = "AVPC",
            condition2 = "High_grade",
            delta_beta_thres = 0.4,
            p_value_thres = 0.05)
