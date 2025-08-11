#!/bin/bash

# fireblade.hardware.summary.sh v0.2
#
# A bash script to parse a host hardware information table.
# It extracts the hostname and counts specific hardware models
# linked to 'fpc' entries on each line. The final output is
# sorted alphabetically by hostname.
#
# Usage: ./script_name.sh /path/to/your/table.file
#

# --- Argument and File Check ---
# Ensure exactly one argument (the file path) is provided.
if [ "$#" -ne 1 ]; then
  echo "Error: Incorrect number of arguments."
  echo "Usage: $0 <file_path>"
  exit 1
fi

TABLE_FILE=$1

# Check if the provided argument is a readable file.
if [ ! -f "$TABLE_FILE" ]; then
  echo "Error: File not found or is not a regular file: '$TABLE_FILE'"
  exit 1
fi

# --- Main Processing and Sorting ---
# The entire output of the 'while' loop is piped to the 'sort' command.
# The input to the loop is now filtered with `grep .` to remove any
# empty or blank lines, preventing them from interfering with the read loop.
while IFS= read -r line; do
  # 2.1: Extract the hostname.
  # This uses grep with a Perl-compatible regex lookbehind to find the string
  # inside the first pair of single quotes.
  host_name=$(echo "$line" | grep -oP "(?<=\(')[^']+(?=')")

  # This check is now mostly a safeguard, as blank lines are pre-filtered.
  if [ -z "$host_name" ]; then
    continue
  fi

  # Extract the content within the curly braces {}.
  context=$(echo "$line" | grep -oP "\{.*\}" | sed "s/[{}]//g")

  # 2.2: Initialize counters for each line.
  count_mp=0
  count_p=0
  count_12p=0

  # Process the context string.
  # Use a regex with \K to find all 'fpc...': 'MODEL' pairs.
  # This corrected version makes the single quotes around the fpc key optional ('?'),
  # allowing it to handle inconsistent formatting in the source file.
  models=$(echo "$context" | grep -oP "'?fpc\d+'?\s*:\s*'\K[^']+")

  # Loop through the extracted models to count them.
  for model in $models; do
    case "$model" in
      "EX4300-48MP")
        ((count_mp++))
        ;;
      "EX4300-48P")
        ((count_p++))
        ;;
      "EX2300-C-12P")
        ((count_12p++))
        ;;
    esac
  done

  # 2.3: Print the results to standard output to be piped to 'sort'.
  echo "${host_name},${count_mp},${count_p},${count_12p}"

done < <(grep . "$TABLE_FILE") | sort
