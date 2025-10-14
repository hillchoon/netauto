#!/bin/bash

# fireblade.mac.map.sh is a bash script to
# map mac addresses in a specific VLAN to physical network location
# base on a mac address table throughout the network
# physical network location refers to any physical interfaces,
# names of which follow the pattern of ge/mge-*/0/*

# Define default file paths and VLAN name
LOG_FILE="macdata.log"
OUTPUT_FILE="mac.map.csv"
VLAN_NAME=""

# Function to display usage instructions
usage() {
  echo "Usage: $0 [-f <log_file>] [-o <output_file>] [-n <vlan_name>]"
  echo "Parses a log file to extract MAC, host, and interface information."
  echo "  -f <log_file>    Specify the path to the input log file. Defaults to 'macdata.log'."
  echo "  -o <output_file> Specify the path for the output file. Defaults to 'mac.map.csv'."
  echo "  -n <vlan_name>   (Optional) Specify the VLAN name to search for. If omitted, all VLANs will be processed."
  exit 1
}

# Parse command line arguments
while getopts "f:o:n:" opt; do
  case "$opt" in
    f)
      LOG_FILE="$OPTARG"
      ;;
    o)
      OUTPUT_FILE="$OPTARG"
      ;;
    n)
      VLAN_NAME="$OPTARG"
      ;;
    *)
      usage
      ;;
  esac
done
shift $((OPTIND-1))

# Check if the input file exists
if [ ! -f "$LOG_FILE" ]; then
  echo "Error: Input file '$LOG_FILE' not found."
  exit 1
fi

# Use awk to process the file block by block and extract data
awk -v vlan_name="$VLAN_NAME" '
BEGIN {
  in_block = 0
  hostname = ""
  print "mac,host,interface"
  print "mac,host,interface" > "'"$OUTPUT_FILE"'"
}

/^------------------------------------------------/ {
  in_block = 0
  next
}

/^Host:/ {
  in_block = 1
  hostname = $0
  gsub(/^Host: /, "", hostname)
  gsub(/[[:space:]]+$/, "", hostname)
  next
}

in_block == 1 {
  # Check if a specific VLAN name is provided, or if we should process all lines
  if (vlan_name == "" || $1 == vlan_name) {
    # The MAC address is the second field
    mac = $2
    # Check for a valid interface
    interface = ""
    for (i = 3; i <= NF; i++) {
      if ($i ~ /^(ge|mge|xe|et)-.\/.\/.*$/) {
        interface = $i
        break
      }
    }
    
    if (interface != "") {
      gsub(/\.0$/, "", interface)
      print mac","hostname","interface
      print mac","hostname","interface >> "'"$OUTPUT_FILE"'"
    }
  }
}
' "$LOG_FILE"

echo "Parsing complete. Data saved to '$OUTPUT_FILE'."
