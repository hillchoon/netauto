#!/bin/bash

# Function to display help message
show_help() {
    echo "Usage: $0 -r <range_file> [-t <arp_file> -o <output_file> -m <mac_map_file> | -i <IP_ADDRESS>] [-h]"
    echo ""
    echo "Description:"
    echo "  This script tests IP addresses against all static IP ranges in the range file and enriches ARP data with MAC mapping information."
    echo "  It supports two modes:"
    echo "  1. Testing a single IP address with -i."
    echo "  2. Processing an ARP file with -t, requiring -o and -m for output and MAC mapping."
    echo ""
    echo "Options:"
    echo "  -r <range_file>       Path to the static IP range file (CSV format: cidr,start_ip,end_ip)."
    echo "  -t <arp_file>         Path to the ARP file (CSV format: mac,ip,hostname)."
    echo "  -o <output_file>      Path to the output file for ARP processing results."
    echo "  -m <mac_map_file>     Path to the MAC mapping file (CSV format: mac,host,interface,original_vlan)."
    echo "  -i <IP_ADDRESS>       Single IP address to test against static ranges."
    echo "  -h                    Display this help message and exit."
    echo ""
    echo "Examples:"
    echo "  Test a single IP:"
    echo "    $0 -r tc.static.ip.ranges.csv -i 142.58.6.150"
    echo "  Process ARP file with MAC mapping:"
    echo "    $0 -r tc.static.ip.ranges.csv -t tc.arp.sample.csv -o results.csv -m tc.mac.map.sample.csv"
    echo ""
    echo "Output Format (for -t):"
    echo "  mac,ip,hostname,static_result,switch,interface,original vlan,new vlan"
    echo "  where static_result is 'yes' (in any static range), 'no' (in a subnet but not in any static range), or 'n/a' (not in any subnet)."
    echo "  switch,interface,original vlan,new vlan are 'n/a' if MAC is not found in mac_map_file, otherwise new vlan is 'NAC-UNPRIV'"
    echo "  when the IP falls in static ranges."
}

# Declare associative array to store IP ranges
declare -A ip_ranges

# Declare associative array to store MAC mappings
declare -A mac_info

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
while getopts "r:t:i:o:m:h" opt; do
    case $opt in
        r) range_file="$OPTARG";;
        t) arp_file="$OPTARG";;
        i) test_ip="$OPTARG";;
        o) output_file="$OPTARG";;
        m) mac_map_file="$OPTARG";;
        h) show_help; exit 0;;
        *) show_help; exit 1;;
    esac
done

# Validate input flags
if [ -z "$range_file" ]; then
    echo "Error: Missing range file (-r)"
    show_help
    exit 1
fi
if [ -n "$arp_file" ] && ( [ -z "$output_file" ] || [ -z "$mac_map_file" ] ); then
    echo "Error: Flags -t requires -o and -m"
    show_help
    exit 1
fi
if [ -n "$test_ip" ] && [ -n "$arp_file" ]; then
    echo "Error: Flags -i and -t are mutually exclusive"
    show_help
    exit 1
fi
if [ -z "$test_ip" ] && [ -z "$arp_file" ]; then
    echo "Error: Must provide either arp file (-t) with -o and -m or single test IP (-i)"
    show_help
    exit 1
fi
if [ ! -f "$range_file" ]; then
    echo "Error: Range file '$range_file' not found"
    show_help
    exit 1
fi
if [ -n "$arp_file" ] && [ ! -f "$arp_file" ]; then
    echo "Error: ARP file '$arp_file' not found"
    show_help
    exit 1
fi
if [ -n "$mac_map_file" ] && [ ! -f "$mac_map_file" ]; then
    echo "Error: MAC map file '$mac_map_file' not found"
    show_help
    exit 1
fi

# Read and store IP ranges from file, handling potential Windows line endings
range_count=0
while IFS=',' read -r cidr start_ip end_ip || [[ -n "$cidr" ]]; do
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

# Load MAC map if provided
if [ -n "$mac_map_file" ]; then
    mac_count=0
    while IFS=',' read -r mac host interface original_vlan || [[ -n "$mac" ]]; do
        # Strip carriage returns
        mac=${mac//$'\r'/}
        host=${host//$'\r'/}
        interface=${interface//$'\r'/}
        original_vlan=${original_vlan//$'\r'/}

        # Skip empty or header line
        if [ -z "$mac" ] || [ "$mac" == "mac" ]; then
            continue
        fi

        mac_info["$mac"]="$host,$interface,$original_vlan"
    done < <(tr -d '\r' < "$mac_map_file")
fi

# Function to check if an IP is in any static range
check_ip_in_range() {
    local test_ip=$1
    local test_ip_int=$(ip_to_int "$test_ip")
    local in_subnet=0
    local in_static_range=0

    for range_name in "${!ip_ranges[@]}"; do
        IFS=',' read -r cidr start_ip end_ip <<< "${ip_ranges[$range_name]}"

        # Check if IP is in subnet
        IFS='/' read -r network prefix <<< "$cidr"
        network_int=$(ip_to_int "$network")
        mask=$(( 0xFFFFFFFF << (32 - prefix) ))
        network_start=$(( network_int & mask ))
        network_end=$(( network_start | (0xFFFFFFFF >> prefix) ))
        if [ "$test_ip_int" -ge "$network_start" ] && [ "$test_ip_int" -le "$network_end" ]; then
            in_subnet=1
            # Check if IP is in static range
            start_int=$(ip_to_int "$start_ip")
            end_int=$(ip_to_int "$end_ip")
            if [ "$test_ip_int" -ge "$start_int" ] && [ "$test_ip_int" -le "$end_int" ]; then
                in_static_range=1
            fi
        fi
    done

    if [ "$in_static_range" -eq 1 ]; then
        echo "yes"
    elif [ "$in_subnet" -eq 1 ]; then
        echo "no"
    else
        echo "n/a"
    fi
}

# Process single test IP if provided
if [ -n "$test_ip" ]; then
    if ! validate_ip "$test_ip"; then
        echo "Error: Invalid test IP address: $test_ip"
        exit 1
    fi
    result=$(check_ip_in_range "$test_ip")
    echo "$result"
fi

# Process ARP file if provided
if [ -n "$arp_file" ]; then
    # Clear output file
    : > "$output_file"

    line_count=0
    while IFS= read -r line || [[ -n "$line" ]]; do
        line=${line//$'\r'/}  # Strip carriage returns

        ((line_count++))
        if [ $line_count -eq 1 ]; then
            # Print header with additional fields
            echo "mac,ip,hostname,static,switch,interface,original vlan,new vlan" >> "$output_file"
            continue
        fi

        # Parse data line: mac,ip,hostname (and possibly extra fields)
        IFS=',' read -r mac ip hostname extra <<< "$line"

        # Skip if empty
        if [ -z "$mac" ] || [ -z "$ip" ] || [ -z "$hostname" ]; then
            continue
        fi

        # Validate IP
        if ! validate_ip "$ip"; then
            echo "Warning: Invalid IP in ARP file line $line_count: $ip"
            continue
        fi

        # Get static test result
        static_result=$(check_ip_in_range "$ip")

        # Lookup MAC in mac_info
        switch="n/a"
        interface="n/a"
        original_vlan="n/a"
        new_vlan="n/a"
        if [ -n "${mac_info[$mac]}" ]; then
            IFS=',' read -r switch interface original_vlan <<< "${mac_info[$mac]}"
            if [ "$static_result" = "yes" ]; then
                new_vlan="$original_vlan"
            else
                new_vlan="NAC-UNPRIV"
            fi
        fi

        # Print to output file
        echo "$mac,$ip,$hostname,$static_result,$switch,$interface,$original_vlan,$new_vlan" >> "$output_file"
    done < <(tr -d '\r' < "$arp_file")
fi