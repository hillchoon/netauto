#!/bin/bash

# fireblade.mac.map.v2.sh is a bash script to
# map MAC addresses to their origin  network locations - the network edge interfaces where the host
# are associated to.

# in order to differentiate the input and output data files, this naming convension is recommended:
# a) input file of raw data is named with extended name .log
# b) input/output files of processed data are named with extended name .csv

# input and output files samples to document their desired format

# RAW_MAC_LOG is the raw output file from
# user@linux:~$ python3 netauto/fireblade.mss.py -l garage/hosts.all -c "show ethernet-switching table"
#
# ------------------------------------------------
# Host: bby-acf111-edge-1.managenet.sfu.ca
#
#
# MAC flags (S - static MAC, D - dynamic MAC, L - locally learned, P - Persistent static, C - Control MAC
#            SE - statistics enabled, NM - non configured MAC, R - remote PE MAC, O - ovsdb MAC)
#
#
# Ethernet switching table : 1976 entries, 1976 learned
# Routing instance : default-switch
#     Vlan                MAC                 MAC         Age    Logical                NH        RTR 
#     name                address             flags              interface              Index     ID
#     BMS                 00:0a:5c:1a:05:6b   D             -   ae0.0                  0         0       
#     BMS                 00:0a:5c:a0:a7:0f   D             -   ae0.0                  0         0       
#     BMS                 00:0a:5c:a2:af:fa   D             -   ae0.0                  0         0       
#     BMS                 00:14:2d:65:f7:03   D             -   mge-0/0/47.0           0         0       
#     BMS                 00:14:2d:82:4c:e5   D             -   mge-0/0/46.0           0         0       
#     ...
#     WIRELESS-AP         f4:2e:7f:c9:75:02   D             -   ae0.0                  0         0       
#     WIRELESS-AP         f4:2e:7f:c9:7b:32   D             -   ae0.0                  0         0       
# 
# ------------------------------------------------
# Host: bby-asb893-mgmt-1.managenet.sfu.ca
# 
# 
# MAC flags (S - static MAC, D - dynamic MAC, L - locally learned, P - Persistent static, C - Control MAC
#            SE - statistics enabled, NM - non configured MAC, R - remote PE MAC, O - ovsdb MAC)
# 
# 
# Ethernet switching table : 251 entries, 251 learned
# Routing instance : default-switch
#     Vlan                MAC                 MAC         Age    Logical                NH        RTR 
#     name                address             flags              interface              Index     ID
#     MANAGEMENT          00:0b:dc:00:4d:a5   D             -   xe-0/2/1.0             0         0       
#     MANAGEMENT          00:0b:dc:00:bf:42   D             -   ge-0/2/0.0             0         0       
#     ...
# ------------------------------------------------    
# ...

# TRUNK_INT_CSV is a list of all trunk interfaces, including aggregation links and their members
# this list is an output from bash script fireblade.trunk.int.pop.sh, remark of which explains 
# the details of its data source and process
# format of this list is shown as below:
#
# hostname,interfacename
# bby-acf111-edge-1.managenet.sfu.ca,ge-0/2/0
# bby-acf111-edge-1.managenet.sfu.ca,ge-0/2/1
# bby-acf111-edge-1.managenet.sfu.ca,ae0
# bby-lib5072-edge-1.managenet.sfu.ca,xe-0/2/0
# bby-lib5072-edge-1.managenet.sfu.ca,xe-0/2/1
# ...

# MAC_MAP_CSV is the outputfile of MAC addresses and their origin ingress network interfaces
# format of the output is shown as below:
#
# mac,host,interface
# 00:14:2d:65:f7:03,bby-acf111-edge-1.managenet.sfu.ca,mge-0/0/47
# 00:14:2d:82:4c:e5,bby-acf111-edge-1.managenet.sfu.ca,mge-0/0/46
# 00:1f:25:06:00:ad,bby-acf111-edge-1.managenet.sfu.ca,ge-0/0/9
# 00:40:ae:05:b4:be,bby-acf111-edge-1.managenet.sfu.ca,ge-0/0/8
# ...


# Define default file paths and VLAN name
RAW_MAC_LOG="macdata.log"
TRUNK_INT_CSV="sfu.all.trunk.int.csv"
MAC_MAP_CSV="mac.map.csv"
VLAN_NAME=""

# Function to display usage instructions
usage() {
  echo "Usage: $0 [-m <RAW_MAC_LOG>] [-t <TRUNK_INT_CSV>] [-o <MAC_MAP_CSV>] [-n <vlan_name>]"
  echo "Parses a log file to extract MAC address and origin network interface information."
  echo "  -m <RAW_MAC_LOG>    Specify the path to the input log file. Defaults to 'macdata.log'."
  echo "  -t <TRUNK_INT_CSV>  Input file with host and trunk interface data. Defaults to 'sfu.all.trunk.int.csv'."
  echo "  -o <MAC_MAP_CSV> Specify the path for the output file. Defaults to 'mac.map.csv'."
  echo "  -n <vlan_name>   (Optional) Specify the VLAN name to search for. If omitted, all VLANs will be processed."
  exit 1
}

# Parse command line arguments
while getopts "m:t:o:n:" opt; do
  case "$opt" in
    m)
      RAW_MAC_LOG="$OPTARG"
      ;;
    t)
      TRUNK_INT_CSV="$OPTARG"
      ;; 
    o)
      MAC_MAP_CSV="$OPTARG"
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
if [ ! -f "$RAW_MAC_LOG" ] || [ ! -f "$TRUNK_INT_CSV" ]; then
  echo "Error: Both input files ('$RAW_MAC_LOG' and '$TRUNK_INT_CSV') must exist."
  exit 1
fi

# Use awk to process both files and perform the filtering
awk -v vlan_name="$VLAN_NAME" '
  BEGIN {
    # Set the output field separator to a comma for the final CSV file
    OFS=","
    # Initialize a two-dimensional associative array
    # trunks[hostname][interfacename] = 1
  }

  # Process the trunk file first
  NR == FNR {
    # Set the field separator to a comma for the trunk file only
    FS=","

    # Skip header line
    if (FNR > 1) {
      hostname = $1
      interface = $2
      trunks[hostname, interface] = 1
    }
    next
  }

  # Process the raw_mac_log file after the trunk file is fully loaded
  FNR == 1 {
    # Reset FS to the default (one or more spaces) for the second file
    FS="[ \t]+"

    in_block = 0
    hostname = ""
    print "mac,host,interface,original vlan"
    print "mac,host,interface,original vlan" > "'"$MAC_MAP_CSV"'"
  }

  # Matches the start of a new host block
  /^------------------------------------------------/ {
    in_block = 0
    next
  }

  # Matches the Host: line and starts a new block
  /^Host:/ {
    in_block = 1
    hostname = $0
    gsub(/^Host: /, "", hostname)
    gsub(/[[:space:]]+$/, "", hostname)
    next
  }

  # Within a host block, process mac address lines
  in_block == 1 {

    # Skip header lines that do not contain data
    if ($0 ~ /flags/ || $0 ~ /Ethernet/ || $0 ~ /Routing/ || $0 ~ /Vlan/ || $0 ~ /statistics/) {
      next
    }

    # Check if a specific VLAN name is provided, or if we should process all lines
    if (vlan_name == "" || $2 == vlan_name) {

      mac = $3
      original_vlan = $2
      # interface = $6

      # Locate interface value per pattern
      interface = ""
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^(ge|mge|xe|et)-.\/.\/.*$/) {
          interface = $i
          break
        }
      }

      # If a valid interface was found, check against trunk interface array
      if (interface != "") {

        # Strip the trailing .0
        gsub(/\.0$/, "", interface)

        # Check if the host/interface combination is in our trunks array
        if (!((hostname, interface) in trunks)) {
          # If not, write the line to the output file
          print mac","hostname","interface","original_vlan >> "'"$MAC_MAP_CSV"'"
        }
      }
    }
  }
' "$TRUNK_INT_CSV" "$RAW_MAC_LOG"

echo "Parsing complete. Data saved to '$MAC_MAP_CSV'."
