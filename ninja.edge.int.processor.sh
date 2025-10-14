#!/bin/bash

# Function to display help message
show_help() {
    echo "Usage: $0 -i <edge_int_file> -m <host_map_file> -s <on/off> -o <output_file> [-h]"
    echo ""
    echo "Description:"
    echo "  This script processes edge interfaces and host maps to determine new VLAN settings based on static IP status."
    echo ""
    echo "Options:"
    echo "  -i <edge_int_file>    Path to the edge interface file (CSV format: switch,interface,original vlan)."
    echo "  -m <host_map_file>    Path to the host map file (CSV format: mac,ip,hostname,static,switch,interface,original vlan,new vlan)."
    echo "  -s <on/off>           Switch mode: 'on' to keep original VLAN if any 'yes' in static, 'off' to flip to NAC-UNPRIV if any 'no' in static."
    echo "  -o <output_file>      Path to the output file."
    echo "  -h                    Display this help message and exit."
    echo ""
    echo "Example:"
    echo "  $0 -i tc.edge.int.sample.csv -m tc.host.map.sample.csv -s on -o output.csv"
    echo ""
    echo "Output Format:"
    echo "  switch,interface,original vlan,new_vlan"
}

# Parse command-line options
while getopts "i:m:s:o:h" opt; do
    case $opt in
        i) edge_int_file="$OPTARG";;
        m) host_map_file="$OPTARG";;
        s) switch_mode="$OPTARG";;
        o) output_file="$OPTARG";;
        h) show_help; exit 0;;
        *) show_help; exit 1;;
    esac
done

# Validate input flags
if [ -z "$edge_int_file" ] || [ -z "$host_map_file" ] || [ -z "$switch_mode" ] || [ -z "$output_file" ]; then
    echo "Error: Missing required flags"
    show_help
    exit 1
fi
if [ "$switch_mode" != "on" ] && [ "$switch_mode" != "off" ]; then
    echo "Error: -s must be 'on' or 'off'"
    show_help
    exit 1
fi
if [ ! -f "$edge_int_file" ]; then
    echo "Error: Edge interface file '$edge_int_file' not found"
    show_help
    exit 1
fi
if [ ! -f "$host_map_file" ]; then
    echo "Error: Host map file '$host_map_file' not found"
    show_help
    exit 1
fi

# Clear output file
: > "$output_file"

# Declare associative array for host map: key "switch:interface" -> space-separated list of static values
declare -A interface_statics

# Read host map file, skipping header
line_count=0
while IFS= read -r line || [[ -n "$line" ]]; do
    line=${line//$'\r'/}  # Strip carriage returns

    ((line_count++))
    if [ $line_count -eq 1 ]; then
        continue  # Skip header
    fi

    IFS=',' read -r mac ip hostname static switch interface original_vlan new_vlan <<< "$line"

    # Skip empty lines
    if [ -z "$switch" ] || [ -z "$interface" ] || [ -z "$static" ]; then
        continue
    fi

    key="$switch:$interface"
    interface_statics["$key"]+="$static "
done < <(tr -d '\r' < "$host_map_file")

# Process edge interface file, skipping header if present (assuming no header based on sample)
line_count=0
while IFS= read -r line || [[ -n "$line" ]]; do
    line=${line//$'\r'/}  # Strip carriage returns

    ((line_count++))
    if [ $line_count -eq 1 ] && [[ "$line" =~ ^switch,interface,original\ vlan$ ]]; then
        continue  # Skip header if present
    fi

    IFS=',' read -r switch interface original_vlan <<< "$line"

    # Skip empty lines
    if [ -z "$switch" ] || [ -z "$interface" ] || [ -z "$original_vlan" ]; then
        continue
    fi

    key="$switch:$interface"
    statics="${interface_statics[$key]}"
    statics="${statics% }"  # Trim trailing space

    if [ -z "$statics" ]; then
        # No matching record
        echo "$switch,$interface,$original_vlan,NAC-UNPRIV" >> "$output_file"
        continue
    fi

    # Count number of matching records
    num_matches=$(echo "$statics" | wc -w)

    if [ $num_matches -eq 1 ]; then
        # Single match
        if [ "$statics" = "yes" ]; then
            echo "$switch,$interface,$original_vlan,$original_vlan" >> "$output_file"
        else
            echo "$switch,$interface,$original_vlan,NAC-UNPRIV" >> "$output_file"
        fi
    else
        # Multiple matches
        has_yes=0
        has_no=0
        for static in $statics; do
            if [ "$static" = "yes" ]; then
                has_yes=1
            fi
            if [ "$static" = "no" ]; then
                has_no=1
            fi
        done

        if [ "$switch_mode" = "on" ]; then
            if [ $has_yes -eq 1 ]; then
                echo "$switch,$interface,$original_vlan,$original_vlan" >> "$output_file"
            else
                echo "$switch,$interface,$original_vlan,NAC-UNPRIV" >> "$output_file"
            fi
        elif [ "$switch_mode" = "off" ]; then
            if [ $has_no -eq 1 ]; then
                echo "$switch,$interface,$original_vlan,NAC-UNPRIV" >> "$output_file"
            else
                echo "$switch,$interface,$original_vlan,$original_vlan" >> "$output_file"
            fi
        fi
    fi
done < <(tr -d '\r' < "$edge_int_file")