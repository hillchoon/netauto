#!/bin/bash

# fireblade.ji.installation.vs.hardware.sh v0.1
#
# A bash script to compare hardware and installation summary files.
# It matches hosts between the two files and compares their data,
# reporting whether the installation matches the hardware configuration.
#
# Usage: ./compare_summaries.sh <hardware_file.csv> <installation_file.csv>
#

# --- Argument and File Check ---
# Ensure exactly two arguments are provided.
if [ "$#" -ne 2 ];
  then
    echo "Error: Incorrect number of arguments."
    echo "Usage: $0 <hardware_file.csv> <installation_file.csv>"
    exit 1
fi

HARDWARE_FILE=$1
INSTALL_FILE=$2

# Check if both files exist and are readable.
if [ ! -f "$HARDWARE_FILE" ]; then
  echo "Error: Hardware file not found: '$HARDWARE_FILE'"
  exit 1
fi
if [ ! -f "$INSTALL_FILE" ]; then
  echo "Error: Installation file not found: '$INSTALL_FILE'"
  exit 1
fi

# --- Main Logic ---
# Create an associative array to hold the data from the hardware file.
# The key will be the hostname, and the value will be the rest of the line.
declare -A hardware_data

# Read the hardware file and populate the associative array.
# This version uses parameter expansion for more robust parsing.
while read -r line; do
  # Sanitize the entire line to remove carriage returns.
  line=$(echo "$line" | tr -d '\r')

  # Extract the hostname (everything before the first comma).
  host_name="${line%%,*}"
  # Extract the counts (everything after the first comma).
  counts="${line#*,}"

  if [ -n "$host_name" ]; then
    hardware_data["$host_name"]=$counts
  fi
done < "$HARDWARE_FILE"

# Process the installation file and compare against the hardware data.
# The output of this loop will be piped to 'sort' at the end.
while read -r line; do
  # Sanitize the entire line to remove carriage returns.
  line=$(echo "$line" | tr -d '\r')
  
  # Extract the hostname and counts using parameter expansion.
  host_name="${line%%,*}"
  install_counts="${line#*,}"

  if [ -z "$host_name" ]; then
    continue
  fi

  # Check if the host from the installation file exists in our hardware data.
  if [[ -v hardware_data["$host_name"] ]]; then
    # Retrieve the hardware counts for the current host.
    hw_counts=${hardware_data["$host_name"]}

    # Compare the installation counts with the hardware counts.
    if [ "$install_counts" == "$hw_counts" ]; then
      echo "$host_name,installation completed"
    else
      echo "$host_name,installed members mismatch hardware members"
    fi
  else
    # Optional: Report on hosts found in the installation file but not the hardware file.
    echo "$host_name,host not found in hardware summary"
  fi
done < "$INSTALL_FILE" | sort
