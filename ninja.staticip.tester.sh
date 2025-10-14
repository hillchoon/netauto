#!/bin/bash

# Usage: ./store_ip_ranges.sh -f <range_file> [-t <test_ip_file> -o <output_file> | -i <IP_ADDRESS>]
# Example: ./store_ip_ranges.sh -f tc.static.ip.range.csv -t test_ips.txt -o results.txt
# Example: ./store_ip_ranges.sh -f tc.static.ip.range.csv -i 142.58.6.150

# Declare associative array to store IP ranges
declare -A ip_ranges

# Function to convert IP to integer
ip_to_int() {
    local ip=$1
    local a b c d
    IFS='.' read -r a b c d <<< "$ip"
    echo $(( (a << 24) + (b << 16) + (c << 8) + d ))
}

# Function to validate IP address format
validate_ip() {
    local ip=$1
    if [[ ! $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        return 1
    fi
    local a b c d
    IFS='.' read -r a b c d <<< "$ip"
    for oct in $a $b $c $d; do
        if [ "$oct" -lt 0 ] || [ "$oct" -gt 255 ]; then
            return 1
        fi
    done
    return 0
}

# Function to validate CIDR format and prefix
validate_cidr() {
    local cidr=$1
    if [[ ! $cidr =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$ ]]; then
        return 1
    fi
    local ip prefix
    IFS='/' read -r ip prefix <<< "$cidr"
    if ! validate_ip "$ip"; then
        return 1
    fi
    if [ "$prefix" -lt 0 ] || [ "$prefix" -gt 32 ]; then
        return 1
    fi
    return 0
}

# Parse command-line options
while getopts "f:t:i:o:" opt; do
    case $opt in
        f) range_file="$OPTARG";;
        t) test_ip_file="$OPTARG";;
        i) test_ip="$OPTARG";;
        o) output_file="$OPTARG";;
        *) echo "Usage: $0 -f <range_file> [-t <test_ip_file> -o <output_file> | -i <IP_ADDRESS>]"; exit 1;;
    esac
done

# Validate input flags
if [ -z "$range_file" ]; then
    echo "Error: Missing range file (-f)"
    echo "Usage: $0 -f <range_file> [-t <test_ip_file> -o <output_file> | -i <IP_ADDRESS>]"
    exit 1
fi
if [ -n "$test_ip_file" ] && [ -z "$output_file" ] || [ -z "$test_ip_file" ] && [ -n "$output_file" ]; then
    echo "Error: Flags -t and -o are mutually dependent"
    echo "Usage: $0 -f <range_file> [-t <test_ip_file> -o <output_file> | -i <IP_ADDRESS>]"
    exit 1
fi
if [ -n "$test_ip" ] && [ -n "$test_ip_file" ]; then
    echo "Error: Flags -i and -t are mutually exclusive"
    echo "Usage: $0 -f <range_file> [-t <test_ip_file> -o <output_file> | -i <IP_ADDRESS>]"
    exit 1
fi
if [ -z "$test_ip" ] && [ -z "$test_ip_file" ]; then
    echo "Error: Must provide either test IP file (-t) with -o or single test IP (-i)"
    echo "Usage: $0 -f <range_file> [-t <test_ip_file> -o <output_file> | -i <IP_ADDRESS>]"
    exit 1
fi
if [ ! -f "$range_file" ]; then
    echo "Error: Range file '$range_file' not found"
    exit 1
fi
if [ -n "$test_ip_file" ] && [ ! -f "$test_ip_file" ]; then
    echo "Error: Test IP file '$test_ip_file' not found"
    exit 1
fi

# Read and store IP ranges from file, handling potential Windows line endings
range_count=0
while IFS=',' read -r cidr start_ip end_ip; do
    # Strip carriage return (\r) for Windows line endings
    cidr=${cidr//$'\r'/}
    start_ip=${start_ip//$'\r'/}
    end_ip=${end_ip//$'\r'/}

    # Skip empty lines
    if [ -z "$cidr" ] || [ -z "$start_ip" ] || [ -z "$end_ip" ]; then
        continue
    fi

    # Increment range_count for correct line numbering
    ((range_count++))

    # Debug: Print parsed fields
    # echo "DEBUG: Line $range_count: cidr='$cidr', start_ip='$start_ip', end_ip='$end_ip'"

    # Validate CIDR
    if ! validate_cidr "$cidr"; then
        echo "Warning: Invalid CIDR in line $range_count: $cidr"
        continue
    fi

    # Validate IP addresses
    if ! validate_ip "$start_ip"; then
        echo "Warning: Invalid start IP in line $range_count: $start_ip"
        continue
    fi
    if ! validate_ip "$end_ip"; then
        echo "Warning: Invalid end IP in line $range_count: $end_ip"
        continue
    fi

    # Validate range (start <= end)
    start_int=$(ip_to_int "$start_ip")
    end_int=$(ip_to_int "$end_ip")
    if [ "$start_int" -gt "$end_int" ]; then
        echo "Warning: Invalid range in line $range_count: start IP ($start_ip) > end IP ($end_ip)"
        continue
    fi

    # Validate that start and end IPs are within the subnet
    IFS='/' read -r network prefix <<< "$cidr"
    network_int=$(ip_to_int "$network")
    mask=$(( 0xFFFFFFFF << (32 - prefix) ))
    network_start=$(( network_int & mask ))
    network_end=$(( network_start | (0xFFFFFFFF >> prefix) ))
    if [ "$start_int" -lt "$network_start" ] || [ "$start_int" -gt "$network_end" ] || [ "$end_int" -lt "$network_start" ] || [ "$end_int" -gt "$network_end" ]; then
        echo "Warning: Static range ($start_ip-$end_ip) in line $range_count is not within subnet $cidr"
        continue
    fi

    # Store in associative array
    ip_ranges["range_$range_count"]="$cidr,$start_ip,$end_ip"
done < <(tr -d '\r' < "$range_file")

# If no valid ranges were loaded, exit
if [ $range_count -eq 0 ]; then
    echo "Error: No valid IP ranges found in '$range_file'"
    exit 1
fi

# Function to check if an IP is in any range
check_ip_in_range() {
    local test_ip=$1
    local output_file=$2
    local test_ip_int=$(ip_to_int "$test_ip")
    local found=0
    for range_name in "${!ip_ranges[@]}"; do
        IFS=',' read -r cidr start_ip end_ip <<< "${ip_ranges[$range_name]}"
        # Check if IP is in subnet
        IFS='/' read -r network prefix <<< "$cidr"
        network_int=$(ip_to_int "$network")
        mask=$(( 0xFFFFFFFF << (32 - prefix) ))
        network_start=$(( network_int & mask ))
        network_end=$(( network_start | (0xFFFFFFFF >> prefix) ))
        if [ "$test_ip_int" -ge "$network_start" ] && [ "$test_ip_int" -le "$network_end" ]; then
            # IP is in subnet, check static range
            start_int=$(ip_to_int "$start_ip")
            end_int=$(ip_to_int "$end_ip")
            if [ "$test_ip_int" -ge "$start_int" ] && [ "$test_ip_int" -le "$end_int" ]; then
                if [ -n "$output_file" ]; then
                    echo "$test_ip,yes" >> "$output_file"
                else
                    echo "yes (in range: $range_name, $start_ip-$end_ip within $cidr)"
                fi
                found=1
            else
                if [ -n "$output_file" ]; then
                    echo "$test_ip,no" >> "$output_file"
                else
                    echo "no (in subnet $cidr but not in static range $start_ip-$end_ip)"
                fi
                found=1
            fi
            break
        fi
    done
    if [ "$found" -eq 0 ] && [ -n "$output_file" ]; then
        echo "$test_ip,n/a" >> "$output_file"
    elif [ "$found" -eq 0 ]; then
        echo "n/a (not in any subnet)"
    fi
}

# Process single test IP if provided
if [ -n "$test_ip" ]; then
    if ! validate_ip "$test_ip"; then
        echo "Error: Invalid test IP address: $test_ip"
        exit 1
    fi
    check_ip_in_range "$test_ip" ""
fi

# Process test IP file if provided
if [ -n "$test_ip_file" ]; then
    # Clear output file
    : > "$output_file"
    while IFS= read -r ip; do
        # Strip carriage return for test IP file
        ip=${ip//$'\r'/}
        # Skip empty lines
        if [ -z "$ip" ]; then
            continue
        fi
        if ! validate_ip "$ip"; then
            echo "Warning: Invalid test IP in '$test_ip_file': $ip"
            continue
        fi
        check_ip_in_range "$ip" "$output_file"
    done < <(tr -d '\r' < "$test_ip_file")
fi