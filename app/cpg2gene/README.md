build_gene_names_csv(input_file: str, output_file: str) -> None

Generates a CSV file containing gene names mapped from CpG probe identifiers.

This function reads an input file containing CpG probe identifiers and their associated gene information. It processes the data to extract unique gene names for each probe and writes the results to a CSV file. The output CSV contains two columns: the CpG probe identifier and the corresponding gene name(s). If a probe maps to multiple genes, all gene names are included, separated by a delimiter.

Parameters:
input_file (str): Path to the input file containing CpG probe and gene mapping information.
output_file (str): Path to the output CSV file where the probe-to-gene mapping will be saved.

Returns:
str(outfile): Full Path of output .csv file

Raises:
FileNotFoundError: If the input file does not exist.
IOError: If there is an error reading the input file or writing the output file.

Notes:

- The function assumes the input file is formatted with probe identifiers and gene names in a tabular structure.
- Duplicate mappings are removed to ensure each probe is associated with unique gene names.
- The output CSV can be used for downstream analyses requiring probe-to-gene relationships.
