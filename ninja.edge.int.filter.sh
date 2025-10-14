#!/bin/bash

# Usage: ./script.sh -f input_file -o output_file

while getopts "f:o:" opt; do
  case $opt in
    f) INPUT_FILE="$OPTARG";;
    o) OUTPUT_FILE="$OPTARG";;
    \?) echo "Invalid option -$OPTARG" >&2; exit 1;;
  esac
done

if [ -z "$INPUT_FILE" ] || [ -z "$OUTPUT_FILE" ]; then
  echo "Usage: $0 -f input_file -o output_file"
  exit 1
fi

> "$OUTPUT_FILE"  # Clear output file

current_host=""
trunks=()
members=()

while IFS= read -r line; do
  line="${line//$'\r'/}"  # Strip carriage returns if any

  if [[ "$line" == "------------------------------------------------" ]]; then
    # Process previous block
    for m in "${members[@]}"; do
      IFS=':' read -r intf vlan <<< "$m"
      is_trunk=0
      for t in "${trunks[@]}"; do
        if [[ "$t" == "$intf" ]]; then
          is_trunk=1
          break
        fi
      done
      if [[ $is_trunk -eq 0 ]] && [[ "$vlan" != "trunk" ]]; then
        echo "$current_host,$intf,$vlan" >> "$OUTPUT_FILE"
      fi
    done

    current_host=""
    trunks=()
    members=()
    continue
  fi

  if [[ "$line" =~ ^Host:\  ]]; then
    current_host="${line#Host: }"
    current_host="${current_host#"${current_host%%[![:space:]]*}"}"  # Strip leading spaces
    current_host="${current_host%"${current_host##*[![:space:]]}"}"  # Strip trailing spaces
    continue
  fi

  if [[ -z "$line" ]]; then continue; fi

  # Extract interface: everything before " unit"
  interface="${line%% unit*}"
  interface="${interface#"${interface%%[![:space:]]*}"}"
  interface="${interface%"${interface##*[![:space:]]}"}"

  if [[ "$line" =~ interface-mode\ trunk ]]; then
    trunks+=("$interface")
  elif [[ "$line" =~ vlan\ members ]]; then
    vlan="${line#*members }"
    vlan="${vlan#"${vlan%%[![:space:]]*}"}"
    vlan="${vlan%"${vlan##*[![:space:]]}"}"
    members+=("$interface:$vlan")
  fi

done < "$INPUT_FILE"

# Process the last block
for m in "${members[@]}"; do
  IFS=':' read -r intf vlan <<< "$m"
  is_trunk=0
  for t in "${trunks[@]}"; do
    if [[ "$t" == "$intf" ]]; then
      is_trunk=1
      break
    fi
  done
  if [[ $is_trunk -eq 0 ]] && [[ "$vlan" != "trunk" ]]; then
    echo "$current_host,$intf,$vlan" >> "$OUTPUT_FILE"
  fi
done