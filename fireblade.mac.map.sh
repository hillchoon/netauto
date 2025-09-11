#!/bin/bash

# fireblade.mac.map.sh is a bash script to
# map mac addresses in a specific VLAN to physical network location
# base on a mac address table throughout the network
# physical network location refers to any physical interfaces,
# names of which follow the pattern of ge/mge-*/0/*

# Define default file paths
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
  echo "  -n <vlan_name>   Specify the VLAN name to search for."
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
  # Initialize variables for the current block
  in_block = 0
  hostname = ""
  has_security_2 = 0
  # Print the header to both stdout and the output file
  print "mac,host,interface"
  print "mac,host,interface" > "'"$OUTPUT_FILE"'"
}

# This regex matches the start of a new host block
/^------------------------------------------------/ {
  # End of the previous block
  in_block = 0
  next
}

# This regex matches the Host: line and starts a new block
/^Host:/ {
  # Start of a new host block
  in_block = 1
  hostname = $0
  gsub(/^Host: /, "", hostname)
  gsub(/[[:space:]]+$/, "", hostname) # Strip trailing spaces
  has_security_2 = 0
  next
}

# Look for the specified VLAN name within a host block
in_block == 1 && $1 == vlan_name {
  has_security_2 = 1
  # The MAC address is the second field after the VLAN name
  mac = $2
  # The interface is the field that matches (ge|mge)-x/0/y, x=0-9
  interface = ""
  for (i = 3; i <= NF; i++) {
    if ($i ~ /^(ge|mge)-[0-9]\/0\/.*$/) {
      interface = $i
      sub(/\.0$/, "", interface)
      break
    }
  }

  # Define the dictionary-like structure and print to screen and output file
  if (has_security_2 && interface != "") {
    print mac","hostname","interface
    print mac","hostname","interface >> "'"$OUTPUT_FILE"'"
  }
}
' "$LOG_FILE"

echo "Processing complete. Data saved to '$OUTPUT_FILE'."
