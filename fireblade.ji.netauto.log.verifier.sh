#!/bin/bash

#fireblade.ji.netauto.log.verifier.sh v0.2

#
# A bash script that searches for three specific, hardcoded keywords
# within all files in a given directory.
# This version uses 'zgrep' to also search inside .gz and .tgz files.
#
# Usage: ./fireblade.ji.netauto.log.verifier.sh <directory>
# Example: ./fireblade.ji.netauto.log.verifier.sh /var/log/juniper/
#

# --- Argument Check ---
# Check if the user has provided exactly one argument.
if [ "$#" -ne 1 ]; then
  echo "Error: Incorrect number of arguments."
  echo "Usage: $0 <directory>"
  exit 1
fi

# --- Keyword and Directory Setup ---
# Hardcode the keywords to be searched.
KEYWORD1="Host OS upgrade staged"
KEYWORD2="request system reboot"
KEYWORD3="set will be activated at next reboot"

# The target directory is the first and only command-line argument.
TARGET_DIR=$1

# Check if the argument is a valid directory.
if [ ! -d "$TARGET_DIR" ]; then
  echo "Error: Directory '$TARGET_DIR' not found."
  exit 1
fi

echo "Searching for 3 specific keywords in '$TARGET_DIR'"
echo "---------------------------------"

# --- Main Loop ---
# Use 'find' to locate all files (-type f) within the target directory.
# Pipe the list of files to a 'while read' loop for safe processing.
find "$TARGET_DIR" -type f -print0 | while IFS= read -r -d $'\0' file; do
  # For each file, count the lines matching the keywords.
  # 'zgrep -c' is more efficient as it directly outputs the count.
  # The '-I' flag tells grep to ignore binary files.
  count1=$(zgrep -I -c -- "$KEYWORD1" "$file" 2>/dev/null)
  count2=$(zgrep -I -c -- "$KEYWORD2" "$file" 2>/dev/null)
  count3=$(zgrep -I -c -- "$KEYWORD3" "$file" 2>/dev/null)


  # If zgrep finds no matches, it returns an empty string. Default to 0.
  count1=${count1:-0}
  count2=${count2:-0}
  count3=${count3:-0}

  # Print the result in the specified format for each file.
  echo "${file},${count1},${count2},${count3}"
done

echo "---------------------------------"
echo "Search complete."

