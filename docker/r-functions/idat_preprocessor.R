library(minfi)
library(dplyr)
library(Matrix)
library(stringr)
library(reshape)
library(lattice)
library(jsonlite)
library(minfiData)
library(missMethyl)
library(data.table)
library(RColorBrewer)

DPI <- 300

targets <- read.metharray.sheet("/input", pattern = "SampleSheet.csv")

# read in the raw data from the IDAT files
rgSet <- read.metharray.exp(targets = targets, force = TRUE)

targets$ID <- paste(targets$Prognosis, targets$Sample_Name, sep = ".")
sampleNames(rgSet) <- targets$GSM_ID

array_type <- rgSet@annotation[1]

detP <- detectionP(rgSet)

# Groups & colors
grp <- factor(targets$Prognosis)
cols <- colorRampPalette(brewer.pal(8, "Dark2"))(nlevels(grp))

# Mean detection p-values per sample
m <- colMeans(detP, na.rm = TRUE)

# --- Filter by threshold ---
threshold <- max(0, mean(m) - 2 * sd(m))
title_txt <- sprintf("Mean Detection PVal >= %.5f", threshold)

idx <- which(m >= threshold & !is.na(m))
if (length(idx) == 0) stop("No samples meet the threshold.")

m_f <- m[idx]
labs_f <- colnames(detP)[idx]
grp_f <- droplevels(grp[idx])

# --- Sort bars (greatest -> smallest), keeping labels/groups aligned ---
ord <- order(m_f, decreasing = FALSE, na.last = NA)
m_f <- m_f[ord]
labs_f <- labs_f[ord]
grp_f <- grp_f[ord]

# Robust color mapping (works even after droplevels)
if (is.null(names(cols))) names(cols) <- levels(grp)
col_map <- cols
cols_f <- unname(col_map[as.character(grp_f)])

# Legend only for the groups shown (preserving original order)
legend_lvls <- names(col_map)[names(col_map) %in% levels(grp_f)]
legend_cols <- unname(col_map[legend_lvls])

# --- Device sizing to stay ~square ---
n <- length(m_f)
cex_names <- max(0.45, min(0.9, 1.1 - 0.007 * n))
left_in <- 0.5 + 0.07 * max(nchar(labs_f)) * cex_names
target_aspect <- 1
min_h <- 5
max_h <- 7.5
w_in <- max(7, 4 + left_in)
h_in <- min(max(min_h, w_in / target_aspect), max_h)

xmax <- max(m_f, na.rm = TRUE)
xlim <- c(0, xmax * 1.1)

png("/output/mean_detection_pvals.png",
  width = w_in, height = h_in, units = "in", res = DPI, type = "cairo"
)

op <- par(no.readonly = TRUE)
on.exit(par(op))
par(mfrow = c(1, 1), mai = c(0.5, left_in, 0.35, 0.25))

barplot(m_f,
  horiz = TRUE,
  col = cols_f,
  names.arg = labs_f,
  las = 1,
  cex.names = cex_names,
  xlab = "Mean detection p-values",
  xlim = xlim,
  space = 0.12,
  main = title_txt,
  cex.main = 1.0
)

legend("bottomright", legend = legend_lvls, fill = legend_cols, bg = "white", bty = "n")
dev.off()

# Control Strip Plot (for Bisulfite Conversion I and II)
.isRGOrStop <- function(object) {
  if (!is(object, "RGChannelSet")) {
    stop(
      "object is of class '", class(object), "', but needs to be of ",
      "class 'RGChannelSet' or 'RGChannelSetExtended'"
    )
  }
}

mycontrolStripPlot <- function(rgSet,
                               controls = c(
                                 "BISULFITE CONVERSION I",
                                 "BISULFITE CONVERSION II"
                               ),
                               sampNames = NULL, xlim = c(5, 17)) {
  .isRGOrStop(rgSet)

  r <- getRed(rgSet)
  g <- getGreen(rgSet)

  for (controlType in controls) {
    ctrlAddress <- getControlAddress(rgSet, controlType = controlType)

    # Red channel
    ctlWide <- as.matrix(log2(r[ctrlAddress, , drop = FALSE]))
    if (!is.null(sampNames)) colnames(ctlWide) <- sampNames
    ctlR <- reshape2::melt(ctlWide, varnames = c("address", "sample"), value.name = "value")

    # Green channel
    ctlWide <- as.matrix(log2(g[ctrlAddress, , drop = FALSE]))
    if (!is.null(sampNames)) colnames(ctlWide) <- sampNames
    ctlG <- reshape2::melt(ctlWide, varnames = c("address", "sample"), value.name = "value")

    # Plot
    ctl <- rbind(
      cbind(channel = "Red", ctlR),
      cbind(channel = "Green", ctlG)
    )
    if (any((ctl$value < xlim[1]) | (ctl$value > xlim[2]))) {
      message("Warning: ", controlType, " probes outside plot range")
    }
    fig <- lattice::xyplot(
      sample ~ value | channel,
      groups = channel, horizontal = TRUE, pch = 19,
      col = c("darkgreen", "darkred"),
      xlab = "Log2 Intensity",
      xlim = xlim,
      main = paste("Control:", controlType),
      layout = c(2, 1),
      data = ctl,
      panel = function(x, y, ...) {
        lattice::panel.stripplot(x, y, ...)
        lattice::panel.abline(h = (as.numeric(y) - 0.5), lty = 3, col = "grey70")
      }
    )
    print(fig)
  }
}

# Save the BISULFITE CONVERSION II plot at 300 dpi
png("/output/bisulfite_conversionII.png",
  width = 3.1 * w_in, height = 1.8 * h_in, units = "in", res = DPI, type = "cairo"
) # drop type if not available
mycontrolStripPlot(rgSet, "BISULFITE CONVERSION II")
dev.off()

# remove poor quality samples
keep <- colMeans(detP) < 0.05
rgSet <- rgSet[, keep]

# remove poor quality samples from targets data
targets <- targets[keep, ]

# remove poor quality samples from detection p-value table
detP <- detP[, keep]

# normalize the data; this results in a GenomicRatioSet object
mSetSq <- preprocessFunnorm(rgSet)

# create a MethylSet object from the raw data for plotting
mSetRaw <- preprocessRaw(rgSet)

png("/output/qc_plot.png",
  width = 7, height = 5, units = "in", res = DPI, type = "cairo"
) # drop type if not available

# Draw the plot
qc <- getQC(mSetRaw)
plotQC(qc, badSampleCutoff = 10)

# Close device (writes the file)
dev.off()

# FILTERING

# ensure probes are in the same order in the mSetSq and detP objects
detP <- detP[match(featureNames(mSetSq), rownames(detP)), ]

# remove any probes that have failed in one or more samples
keep <- rowSums(detP < 0.01) == ncol(mSetSq)

mSetSqFlt <- mSetSq[keep, ]

# remove probes with SNPs at CpG site
mSetSqFlt <- dropLociWithSnps(mSetSqFlt)

# exclude cross reactive probes
xReactiveProbes <- maxprobes::xreactive_probes(array_type = "450K")
xReactiveProbes <- unlist(xReactiveProbes)
keep2 <- !(featureNames(mSetSqFlt) %in% xReactiveProbes)
mSetSqFlt <- mSetSqFlt[keep2, ]

# Get BVal Matrix
bVals <- getBeta(mSetSqFlt)
bVals_df <- as.data.frame(bVals)

# Groups & colors
grp <- factor(targets$Prognosis)
cols <- colorRampPalette(brewer.pal(8, "Dark2"))(nlevels(grp))

# Save at 300 dpi (7x5 inches -> 2100x1500 px)
png("/output/beta_density.png", width = 7, height = 5, units = "in", res = DPI)
par(mfrow = c(1, 1), mar = c(5, 4, 2, 1))
densityPlot(bVals,
  sampGroups = grp,
  col = cols,
  main = "Density Plot",
  legend = FALSE,
  xlab = "BVals"
)
legend("top", legend = levels(grp), text.col = cols, bty = "n")
dev.off()

# Remove values that are either <= 0 or >=1 in
# order to avoid inf error in PCA dim reduction
rows_to_keep <- apply(bVals_df, 1, function(row) all(row > 0 & row < 1))
bVals_df <- bVals_df[rows_to_keep, ]

rows_to_keep2 <- apply(bVals_df, 1, function(row) all(row < 0.3 | row > 0.6))
bVals_df <- bVals_df[rows_to_keep2, ]

bVals_df_fin <- t(bVals_df)
bVals_df_fin <- as.data.frame(bVals_df_fin)
rownames(targets) <- targets$GSM_ID
bVals_df_fin$Prognosis <- targets[rownames(bVals_df_fin), "Prognosis"]

write.csv(bVals_df_fin, file = "/output/bval_data.csv", row.names = FALSE)

if (array_type == "IlluminaHumanMethylationEPICv2") {
  arr_typ <- "epicv2"
} else if (array_type == "IlluminaHumanMethylationEPIC") {
  arr_typ <- "epic"
} else if (array_type == "IlluminaHumanMethylation450k") {
  arr_typ <- "450k"
} else {
  arr_typ <- NA  # default if no match
}

num_idat <- length(list.files("/input", pattern = "\\.idat$", full.names = TRUE, ignore.case = TRUE))
unique_categories <- unique(bVals_df_fin$Prognosis)
unique_categories_length <- length(unique_categories)
prognosis_column <- "Prognosis"
tag_value_counts <- bVals_df_fin %>% count(Prognosis)
dict_counts <- as.list(setNames(tag_value_counts$n, tag_value_counts$Prognosis))
completion_time <- Sys.time()

# Wrap everything in a list
all_data <- list(
  analysis_time=completion_time,
  idat_file_number=num_idat,
  detected_illumina_array_type=arr_typ,
  prognosis_column=prognosis_column,
  prognosis_value_counts=unique_categories_length,
  prognosis_unique_values=unique_categories,
  prognosis_distribution=dict_counts
)

json_data <- toJSON(all_data, pretty = TRUE, auto_unbox = TRUE)
write(json_data, file = "/output/metadata.json")