#!/bin/bash

#fireblade.ji.netauto.log.verifier.sh v0.1

#
# A bash script that takes two keywords and a directory. For each file
# in the directory, it counts the number of lines matching each keyword.
# This version uses 'zgrep' to also search inside .gz and .tgz files.
#
# Usage: ./fireblade.ji.verifier.sh <keyword1> <keyword2> <directory>
# Example: ./fireblade.ji.verifier.sh "error" "warning" /var/log
#

# --- Argument Check ---
# Check if the user has provided exactly three arguments.
if [ "$#" -ne 3 ]; then
  echo "Error: Incorrect number of arguments."
  echo "Usage: $0 <keyword1> <keyword2> <directory>"
  exit 1
fi

# Store the arguments in variables for clarity.
KEYWORD1=$1
KEYWORD2=$2
TARGET_DIR=$3

# Check if the third argument is a valid directory.
if [ ! -d "$TARGET_DIR" ]; then
  echo "Error: Directory '$TARGET_DIR' not found."
  exit 1
fi

echo "Searching for Keyword 1 ('$KEYWORD1') and Keyword 2 ('$KEYWORD2') in '$TARGET_DIR'"
echo "---------------------------------"

# --- Main Loop ---
# Use 'find' to locate all files (-type f) within the target directory.
# Pipe the list of files to a 'while read' loop for safe processing,
# even if filenames contain spaces or special characters.
find "$TARGET_DIR" -type f -print0 | while IFS= read -r -d $'\0' file; do
  # For each file, count the lines matching the first keyword.
  # 'zgrep -c' is more efficient as it directly outputs the count.
  # The '-I' flag tells grep to ignore binary files.
  count1=$(zgrep -I -c -- "$KEYWORD1" "$file" 2>/dev/null)

  # For each file, count the lines matching the second keyword.
  count2=$(zgrep -I -c -- "$KEYWORD2" "$file" 2>/dev/null)

  # If zgrep finds no matches, it returns an empty string. Default to 0.
  count1=${count1:-0}
  count2=${count2:-0}

  # Print the result in the specified format for each file.
  echo "${file},${count1},${count2}"
done

echo "---------------------------------"
echo "Search complete."
 
