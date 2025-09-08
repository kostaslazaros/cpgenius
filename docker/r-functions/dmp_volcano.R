library(glue)
library(limma)
library(ggplot2)
library(ggrepel)
library(dplyr)
library(optparse)
library(jsonlite)

option_list <- list(
  make_option(c("-c", "--csv_path"), type = "character", default = NULL,
              help = "Path to CSV file", metavar = "character"),
  make_option(c("-1", "--condition1"), type = "character", default = NULL,
              help = "First condition", metavar = "character"),
  make_option(c("-2", "--condition2"), type = "character", default = NULL,
              help = "Second condition", metavar = "character"),
  make_option(c("-d", "--delta_beta"), type = "numeric", default = 0.4,
              help = "Delta beta threshold", metavar = "numeric"),
  make_option(c("-p", "--p_value"), type = "numeric", default = 0.05,
              help = "P-value threshold", metavar = "numeric")
)

opt_parser <- OptionParser(option_list = option_list)
opt <- parse_args(opt_parser)

dmp_volcano <- function(csv_path, condition1, condition2, delta_beta_thres, p_value_thres) {
  # Comparison Groups
  comp_vec <- c(condition1, condition2)

  filname <- glue("/output/dmps_{comp_vec[1]}_vs_{comp_vec[2]}_db{delta_beta_thres}_pval{p_value_thres}")
  png_name <- paste0(filname, ".png")
  csv_name <- paste0(filname, ".csv")
  json_name <- paste0(filname, ".json")

  # Read beta-values matrix from disk
  bvals <- read.csv(file=csv_path,
                    header=TRUE,
                    stringsAsFactors=TRUE)

  bvals <- bvals[bvals$Prognosis %in% comp_vec, , drop = FALSE]

  tag_value_counts <- bvals %>% count(Prognosis)
  dict_counts <- as.list(setNames(tag_value_counts$n, tag_value_counts$Prognosis))

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
    # ggtitle(glue::glue("DMPs ({comp_vec[1]} vs {comp_vec[2]})"))
    ggtitle(glue::glue("DMPs ({comp_vec[1]} vs {comp_vec[2]})"), 
            subtitle = glue::glue("deltaBeta: {delta_beta_thres}, p-value: {p_value_thres}")) +
    theme(plot.subtitle = element_text(hjust = 0.5, size = 15))

  # Adding labels with ggrepel for better visibility and avoiding overlaps
  p_labeled <- p + geom_label_repel(data=df_annotated, aes(label=rownames(df_annotated), x=deltaBeta, y= -log10(P.Value)),
                                             box.padding=0.35, point.padding = 0.5,
                                             size=6, segment.color='grey50', show.legend=FALSE)

  ggsave(file = png_name,
                  plot = p_labeled, width = 11, height = 6, units = "in", dpi = 300, bg = "white")

  DMPs <- subset(DMPs, diffexpressed %in% c("UP", "DOWN"))
  DMPs <- cbind(Feature = rownames(DMPs), DMPs)

  write.csv(DMPs, file = csv_name, row.names = FALSE)
  
  completion_time <- Sys.time()
  
  # Wrap everything in a list
  all_data <- list(
    analysis_time=completion_time,
    compared_conditions=comp_vec,
    delta_beta_threshold=delta_beta_thres,
    pvalue_threshold=p_value_thres,
    condition_distribution=dict_counts
  )
  
  json_data <- toJSON(all_data, pretty = TRUE, auto_unbox = TRUE)
  write(json_data, file = json_name)
}


dmp_volcano(csv_path = "/input/bval_data.csv",
            condition1 = opt$condition1,
            condition2 = opt$condition2,
            delta_beta_thres = opt$delta_beta,
            p_value_thres = opt$p_value)
