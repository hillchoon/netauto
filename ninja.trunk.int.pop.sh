#!/bin/bash

# Define default file paths
INPUT_FILE="input.file"
OUTPUT_FILE="output.file"

# Function to display usage instructions
usage() {
  echo "Usage: $0 [-i <input_file>] [-o <output_file>]"
  echo "Parses a trunk interface log file to extract host and trunk interface information."
  echo "  -i <input_file>  Specify the path to the input log file. Defaults to 'sfu.all.trunk.interfaces.log'."
  echo "  -o <output_file> Specify the path for the output file. Defaults to 'trunk.map.csv'."
  exit 1
}

# Parse command line arguments
while getopts "i:o:" opt; do
  case "$opt" in
    i)
      INPUT_FILE="$OPTARG"
      ;;
    o)
      OUTPUT_FILE="$OPTARG"
      ;;
    *)
      usage
      ;;
  esac
done
shift $((OPTIND-1))

# Check if the input file exists
if [ ! -f "$INPUT_FILE" ]; then
  echo "Error: Input file '$INPUT_FILE' not found."
  exit 1
fi

# Use awk to process the file block by block and extract data
awk '
BEGIN {
  in_block = 0
  hostname = ""
  print "hostname,interfacename"
  print "hostname,interfacename" > "'"$OUTPUT_FILE"'"
}

# Matches the Host: line and starts a new block
/^Host:/ {
  in_block = 1
  hostname = $0
  gsub(/^Host: /, "", hostname)
  gsub(/[[:space:]]+$/, "", hostname)
  next
}

# Matches the end of a block
/^------------------------------------------------/ {
  in_block = 0
  next
}

# Within a block, if the line is not empty, process it as an interface
in_block == 1 && $0 !~ /^[[:space:]]*$/ {
  interfacename = $0
  gsub(/[[:space:]]+$/, "", interfacename)
  print hostname","interfacename
  print hostname","interfacename >> "'"$OUTPUT_FILE"'"
}
' "$INPUT_FILE"

echo "Parsing complete. Data saved to '$OUTPUT_FILE'."
