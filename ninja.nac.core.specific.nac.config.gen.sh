#!/bin/bash

'''
This generator takes options of interfaces in below format and generate specific NAC configuration for core routers
$ nac.core.specific.nac.config.gen.sh 11,12,13,14,15...
'''

# Check if input is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <interface_numbers>"
    echo "Example: $0 11,12,13,14,15"
    exit 1
fi

# Get the comma-separated list of interface numbers
IFS=',' read -r -a interfaces <<< "$1"

# Define VLANs to generate configurations for
vlans=(13 513)

# Loop through each interface number
for intf in "${interfaces[@]}"; do
    # Remove any whitespace
    intf=$(echo "$intf" | tr -d '[:space:]')
    # Loop through each VLAN
    for vlan in "${vlans[@]}"; do
        # Generate interface configuration
        echo "set interfaces ae${intf} unit ${vlan} proxy-arp restricted"
        echo "set interfaces ae${intf} unit ${vlan} vlan-id ${vlan}"
        echo "set interfaces ae${intf} unit ${vlan} family inet targeted-broadcast forward-only"
        echo "set interfaces ae${intf} unit ${vlan} family inet unnumbered-address irb.${vlan}"
    done
done

# Generate DHCP relay configurations
for intf in "${interfaces[@]}"; do
    # Remove any whitespace
    intf=$(echo "$intf" | tr -d '[:space:]')
    for vlan in "${vlans[@]}"; do
        echo "set forwarding-options dhcp-relay group DHCP-INTERFACES interface ae${intf}.${vlan}"
    done
done
