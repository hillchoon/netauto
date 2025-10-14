#!/bin/bash

# Define default file paths
MAC_FILE="input.file"
TRUNK_FILE="sfu.all.trunk.int.csv"
OUTPUT_FILE="filtered.mac.csv"

# Function to display usage instructions
usage() {
  echo "Usage: $0 [-m <mac_file>] [-t <trunk_file>] [-o <output_file>]"
  echo "Filters a MAC address table to exclude entries on trunk interfaces."
  echo "  -m <mac_file>    Input file with MAC, host, and interface data. Defaults to 'sfu.all.mac.csv'."
  echo "  -t <trunk_file>  Input file with host and trunk interface data. Defaults to 'sfu.all.trunk.int.csv'."
  echo "  -o <output_file> Output file for the filtered data. Defaults to 'filtered.mac.csv'."
  exit 1
}

# Parse command line arguments
while getopts "m:t:o:" opt; do
  case "$opt" in
    m)
      MAC_FILE="$OPTARG"
      ;;
    t)
      TRUNK_FILE="$OPTARG"
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

# Check if the input files exist
if [ ! -f "$MAC_FILE" ] || [ ! -f "$TRUNK_FILE" ]; then
  echo "Error: Both input files ('$MAC_FILE' and '$TRUNK_FILE') must exist."
  exit 1
fi

# Use awk to process both files and perform the filtering
awk '
  BEGIN {
    FS=","
    OFS=","
    # Initialize a two-dimensional associative array
    # trunks[hostname][interfacename] = 1
  }

  # Process the trunk file first
  NR == FNR {
    # Skip header line
    if (FNR > 1) {
      hostname = $1
      interface = $2
      trunks[hostname, interface] = 1
    }
    next
  }

  # Process the MAC file after the trunk file is fully loaded
  FNR == 1 {
    # Print the header to the output file
    print "mac,host,interface" > "'"$OUTPUT_FILE"'"
  }

  # For all other lines in the MAC file
  FNR > 1 {
    mac = $1
    host = $2
    interface = $3
    
    # Check if the combination of host and interface exists in our trunks array
    if (!((host, interface) in trunks)) {
      # If not, write the line to the output file
      print mac, host, interface >> "'"$OUTPUT_FILE"'"
    }
  }
' "$TRUNK_FILE" "$MAC_FILE"

echo "Filtering complete. Non-trunk MAC entries saved to '$OUTPUT_FILE'."
