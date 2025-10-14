README for NAC Data Processing

# Retrieve Raw Data

## 1. Trunk Interface Data
Run Netauto for trunk/lacp interfaces on all switches/routers
```
~$ python3 netauto/fireblade.mss.py -l garage/hosts.all -c 'show configuration interfaces | display set | match "trunk|802.3ad" | trim 15' | tee sfu.all.trunk.interfaces.rawdata.log
```

## 2. ARP Entries
Run Netauto to retrieve ARP entries of all VLANs in interest on the core
```
~$ python3 netauto/fireblade.mss.py -H <core.fqdn> -c 'show arp | match "irb.<1>|...|irb.<n>"' | save /var/tmp/<corename>.arp.rawdata.log
```

## 3. MAC Entries
Run Netauto to retrieve all MAC entries on the edge networks off from the core in interest
```
~$ python3 netauto/fireblade.mss.py -l <hosts.list> -c 'show ethernet-switching table | match "vlan-name-1|...|vlan-name-n"' | tee <corename>.mac.rawdata.log
```

## 4. All Edge Interfaces in Interested VLANs
Run Netauto to restrive interfaces of interested VLANs on all edge networks off from the core
```
~$ python3 netauto/fireblade.mss.py -l <hosts.list> -c 'show configuration interfaces | display set | trim 15 | match "	vlan-name|...|trunk"' | tee <corename>.edge.interfaces.rawdata.log
```

# Process Raw Data

## 1. Trunk Interface

### Trim Trunk Raw Data
trim `sfu.all.trunk.interfaces.rawdata.log` to `sfu.all.trunk.interfaces.log` in below format by removing extraneous info:
```
------------------------------------------------
Host: bby-acf111-edge-1.managenet.sfu.ca

ge-0/2/0
ge-0/2/1
ae0

------------------------------------------------
Host: bby-lib5072-edge-1.managenet.sfu.ca

xe-0/2/0
xe-0/2/1
ae0
``` 

### Convert Trimmed Data to .csv
Run bash **ninja.trunk.int.pop.sh** to convert `sfu.all.trunk.interfaces.log` to `sfu.all.trunk.int.csv` in below format
```
hostname,interfacename
bby-lib507-edge-1.managenet.sfu.ca,xe-0/2/0
bby-lib507-edge-1.managenet.sfu.ca,xe-0/2/1
bby-lib507-edge-1.managenet.sfu.ca,ae0
```

## 2. Static IP Ranges
Based on M&M, populate `<corename>.static.ip.ranges.csv` as shown below:
```
142.58.6.128/26,142.58.6.129,142.58.6.190
142.58.114.0/24,142.58.114.1,142.58.114.35
142.58.134.0/24,142.58.134.101,142.58.134.180
```

## 3. Match MAC to Its Original Ingress Interfaces
Run **ninja.mac.map.sh** to match all MAC addresses to their original ingress interfaces
```
~$ ninja.mac.map.sh -m <corename>.mac.rawdata.log -t sfu.all.trunk.int.csv -o <corename>.mac.map.csv
```

## 4. Assemble Host Data Set
### Process ARP Raw Data
Convert `<corename>.arp.rawdata.log` to `<corename>.arp.csv` by removing of extraneous info and adding ',' as seperator shown below:
```
mac,ip,hostname,static,switch,interface,orig inal vlan,new vlan
54:bf:64:98:cd:be,142.58.113.21,bsblabc14.bus.sfu.ca
6c:3c:8c:3d:93:e8,142.58.113.22,bsblaba1.bus.sfu.ca
6c:2b:59:c7:a0:5e,142.58.113.24,bsblaba28.bus.sfu.ca
```
### Process Host ARP, Ingress Interface, Static IP Flag & Original VLAN
Run **ninja.hostinfo.processor.sh** to:
* update column static in `<corename>.arp.csv` with test result of against static ip ranges in `<corename>.static.ip.ranges.csv`, and 
* update columns switch, interface, original vlan with switch, interface, original vlan info of matching mac from `<corename>.mac.map.csv`, and
* update new vlan with proper value depends on whether the IP is static.
```
ninja.hostinfo.processor.sh -r <corename>.static.ip.ranges.csv -t <corename>.arp.csv -m <corename>.mac.map.csv -o <corename>.hosts.map.csv
```
## 5. NAC Interfaces
### Process Edge Interface Raw Data
Run **ninja.edge.int.filter.sh** to extract edge interface from `<corename>.edge.interfaces.rawdata.log`
```
~$ ninja.edge.int.filter.sh -f <corename>.edge.interfaces.rawdata.log -o <corename>.edge.int.csv
```
### Set New VLAN Value
Run **ninja.edge.int.processor.sh** to set new vlan value for all interfaces in `<corename>.edge.int.csv`, according to whether the interface has any host with static IP in `<corename>.host.map.csv`
```
~$ ninja.edge.int.processor.sh -i <corename>.edge.int.csv -m <corename>.host.map.csv -o <corename>.nac.int.csv -s on/off
```
### Generate/Push Change Commands to Edge Switches
Run Netauto to generate interface vlan change commands and commit at specific date/time
```
~$ python3 fireblade.vlan.flip.py -c <corename>.nac.int.csv -m ...
```
