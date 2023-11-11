**Last updated on November 10, 2023.**

# Table of Content
1. [Introduction](#introduction)
2. [You as A User](#you-as-a-user)
3. [Common Command Line Arguments](#common-command-line-arguments)
4. [fireblade.mss](#fireblademss)
5. [JUNOS Installation](#firebladeji)
6. [Inactive Interfaces Inventory](#firebladeii)
7. [II Agent](#portusageslax)
8. [Legacy Fireblade](#firebladepylegacy))
9. [Root Password Generator](#firebladerootpass)
10. [Hardware Probe](#firebladehardwareprobe)
## Introduction

Netauto is a set of Python3 tools developed for managing and operating Juniper Network in Enterprise Network Operations.

## You as A User
### 1. A NOC User
A Netauto's Runtime Environment should be ready for a NOC user to perform operation and management tasks on the managed network hosts - Juniper Network equipment. 
Netauto's Runtime Environment includes:  
1) A management server granted with SSH and NETCONF access to production network.  
2) Necessary software and libaries installed on the management server. Those software and libraries are Python3 and its libraries, Netauto, Juniper Network Junos PyEZ Python Library, and some third-party libraries. Besides Netauto, these software and libraries should be installed and updated to latest versions by a sudo user of the management server. Netauto is installed and updated by NOC user with below commands. **NOTE**: please keep Netauto updated to the latest version.  
```
# installation:
$ git clone https://github.com/hillchoon/utils
$ git clone https://github.com/hillchoon/netauto
$ cd ~/netauto
$ git submodule update --init
$ cd

# update netauto to latest version:
$ cd ~/netauto
$ git pull
$ cd

# update netauto's submodule utils to latest version:
$ cd ~/utils
$ git pull
$ cd ~/netauto/utils
$ git checkout origin
$ cd
```
4) A NOC user is granted with read-only acces to a list of managed network hosts on the production network. This list is created and maintained by sudo users, and it could be a text file with hosts' IP address or FQDN.  
5) Managed network hosts shall be configured to allow SSH and NETCONF sessions initiated from management server.
### 2. A SUDO User
Installs Python3, Junos PyEZ, and other third-party libraries (listed per Netauto script if any depedency).  
```
$ pip3 install junos-eznc
```
## Common Command Line Arguments
A common command line to launch a Netauto script is:
```
$ python3 <directory-of-a-netauto-script> <argument-of-managed-hosts> <argument-of-commands> <other-arguments>
```
**argument-of-managed-hosts**  
This argument could be:  
1) the directory to a text file of hosts' IP or FQDN. i.e. ~/garage/hosts.all, or  
2) a list of FQDN of hosts with a space in between. i.e.\
   ```
   host1.domain.com host2.domain.com host3.domain.com
   ```

**argument-of-commands**  
Netauto drives different features for pulling information and pushing configuration changes, therefore this arugument is for either query or configuration, not a mix of both.  
This argument could be:
1) the directory to a text file of JUNOS commands, or  
2) a list of quoted commands with a space in between. i.e. \
   ```
   'show system information | match "keyword"'[space]'show system uptime'[space]'show interfaces ge-0/0/0 extensive | match "error"'
   ```
**hidden switch in a list of host or commands**
All Fireblade Netauto scripts support a hidden switch in a file of hosts or commands. This switch comes in handy when you want the scripts to toggle some of the hosts or commands without having to delete them. To do that, a '#' shall be added at the begining of the line, see examples below:
```
$ cat ~/garage/hosts.campus.a # host3.com will be skipped
host1.com
host2.com
#host3.com
host4.com
$ cat ~/garage/cli.show # command 'show system uptime' will be skipped
show system information
show interfaces terse irb
show ethernet-switching table
#show system uptime
show spanning-tree statistics interface
$
```
## fireblade.mss
v1.0\
It is happening, **simultaneously**! \
Introducing fireblade.mss for **m**ultiple **s**ession**s**.
### Key Features:
1) 50 simultaneous sessions from management server to managed hosts at a time;
2) Flexible input of multiple hosts and commands as command line arguments;
3) Filter target hosts with arguments of campus, role, chassis model;
4) Silencer to mute output for hosts that mismatch given creteria.
See details below from command line argument '-h'.

### Command Line Arguments
```
usage: fireblade.mss.py [-h] (-H HOSTS [HOSTS ...] | -l FILE)
                        [-c COMMANDS [COMMANDS ...] | -f FILE]
                        [-m {show,testride,comconf,commit}] [-p {bby,sry,van}]
                        [-r {all,core,edge,dc,ext,mgmt}] [-d {all,c,p,mp,m}]
                        [-s]

General Queries & Configuration Changes Tool

optional arguments:
  -h, --help            show this help message and exit
  -H HOSTS [HOSTS ...], --hosts HOSTS [HOSTS ...]
                        hosts' FQDN in format of 'host1' 'host2'...single and
                        double quote function the same.
  -l FILE, --host_list FILE
                        Direcotry to a list of hosts.
  -c COMMANDS [COMMANDS ...], --commands COMMANDS [COMMANDS ...]
                        command(s) in format of "command1" "command2"...single
                        and double quote function the same.
  -f FILE, --cmdfile FILE
                        Directory to a cli command file.
  -m {show,testride,comconf,commit}, --mode {show,testride,comconf,commit}
                        Operation mode: Default to "show". Other choices are
                        "testride" for testing configuration, "comconf" for
                        "commit confirm" with input minutes, and "commit".
  -p {bby,sry,van}, --campus {bby,sry,van}
                        Campus: self-explanatory. All campuses are covered if
                        no option of campus is provided.
  -r {all,core,edge,dc,ext,mgmt}, --role {all,core,edge,dc,ext,mgmt}
                        Chassis role: Default to "all" for all chassis. Other
                        choices are: "core" for CORE switches; "edge" for EDGE
                        switches; "ext" for EXTENSION switches; "dc" for
                        DATACENTRE switches, and "mgmt" for MANAGEMENT
                        network.
  -d {all,c,p,mp,m}, --model {all,c,p,mp,m}
                        Chassis model: Default to "all" for all models,other
                        choices are "c" for "EX2300-C-12P", "p" for
                        "EX4300-48P", "mp" for "EX4300-48MP",and "m" for
                        manual input.
  -s, --silencer        Silence the output for mismatch hosts.

```
### example 1 - make queries on 2 hosts
```
$ python3 ~/netauto/fireblade.mss.py -H host1.domain.com host2.domain.com -c 'show system information' 'show ethernet-switching table vlan-name DATA | except "ae0"'
```
### example 2 - test a change on multiple hosts
```
$ python3 ~/netauto/fireblade.mss.py -l ~/garage/hosts.all -f ~/garage/cli.adding.vlan.abc -m testconfig
```
### example 3 - apply a change on multiple hosts
```
$ python3 ~/netauto/fireblade.mss.py -l ~/garage/hosts.all -f ~/garage/cli.removing.vlan.xyz -m commit
```
## fireblade.ji
v0.83\
Introducing fireblade.ji for **J**unos **I**nstallation
### Key Features
1) 100 simultaneous sessions of Junos Installation at a time;
2) Generates log file for each Junos installation session in directory ./logs/
3) Generates a summary log file for all installation sessions in directory defined by user\
See details below from command line argument '-h'.
### Command Line Arguments
```
usage: fireblade.ji.py [-h] (-H SINGLE_HOST | -l FILE) -x ACTION -s FILE

General Queries & Configuration Changes Tool

optional arguments:
  -h, --help            show this help message and exit
  -H SINGLE_HOST, --single_host SINGLE_HOST
                        FQDN of a host
  -l FILE, --hosts_list FILE
                        Direcotry to a list of hosts
  -x ACTION, --action ACTION
                        action after JUNOS is installed. Default to
                        'rollback', other two options are 'now' for immediate
                        rebooting or time string in format of 'yymmddhh' to
                        complete the software installation. In last option
                        fireblade.ji sets a random time offset 0-20 minutes
                        for a host at the desired hour
  -s FILE, --summary_log FILE
                        Directory to an output file
```
### Example
```
$ python3 netauto/fireblade.ji.py -H <FQDN> -x now -s logs/<filename>.log
Username: M.Schumacher
Password: formula1champion
Directory to JUNOS Package for EX4300-48P: <directory>/software/jinstall-ex-4300-21.4R3-S4.18-signed.tgz
Directory to JUNOS Package for EX4300-48MP: <directory>/software/jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz

JUNOS installation is undergoing and may take hours. Please be patient.

You may track installation progress in below two ways:

1) tail summary log file at logs/<filename>.log to view summary of the progress on targeted hosts, and
2) tail log files named "host-junosinstallation-yyyy-mm-dd.log" for detailed progress on each host


2099-10-24 09:01 <FQDN>: JUNOS installation completed.
2099-10-24 09:01 <FQDN> Post installation action: Shutdown at Tue Oct 24 09:02:15 2099. [pid 56186]
results: 
[(True, '<FQDN>', 'Shutdown at Tue Oct 24 09:02:15 2099. [pid 56186]'), '\n']
$
$ cat logs/<host>-junosinstallation-2099-10-24.log
08:19 request-package-checks-pending-install rpc is not supported on given device
08:19 computing checksum on local package: ../jbackup/software/jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz
08:19 cleaning filesystem ...
08:20 before copy, computing checksum on remote package: /var/tmp/jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz
08:23 b'jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz': 133185536 / 1331797046 (10%)
08:26 b'jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz': 266371072 / 1331797046 (20%)
08:29 b'jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz': 399540224 / 1331797046 (30%)
08:32 b'jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz': 532725760 / 1331797046 (40%)
08:35 b'jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz': 665911296 / 1331797046 (50%)
08:38 b'jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz': 799080448 / 1331797046 (60%)
08:41 b'jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz': 932265984 / 1331797046 (70%)
08:44 b'jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz': 1065451520 / 1331797046 (80%)
08:47 b'jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz': 1198620672 / 1331797046 (90%)
08:50 b'jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz': 1331797046 / 1331797046 (100%)
08:50 after copy, computing checksum on remote package: /var/tmp/jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz
08:50 checksum check passed.
08:50 installing software on VC member: 1 ... please be patient ...
08:58 software pkgadd package-result: 0
Output: 

[Oct 24 08:50:57]: Checking pending install on fpc1

Pushing /var/tmp/jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz to fpc1:/var/tmp/jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed.tgz
Verified jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed signed by PackageProductionECP256_2023 method ECDSA256+SHA256
Pushing Junos image package to the host...
Installing /var/tmp/install-media-ex-4300mp-junos-21.4R3-S4.18-secure.tgz
Extracting the package ...

============================================
Host OS upgrade is FORCED
Current Host kernel version : 3.14.52-rt50-WR7.0.0.9_ovp
Package Host kernel version : 3.14.52-rt50-WR7.0.0.9_ovp
Current Host version        : 3.1.0
Package Host version        : 3.1.0
Min host version required for applications: 3.0.0
============================================

Validate linux image...
upgrade_platform: -------------------
upgrade_platform: Parameters passed:
upgrade_platform: silent=0
upgrade_platform: package=/var/tmp/tmp.WjGubcyRZHjunos_cli_upg/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz
upgrade_platform: clean install=0
upgrade_platform: on primary   =0
upgrade_platform: clean upgrade=0
upgrade_platform: Need reboot after staging=1
upgrade_platform: -------------------
upgrade_platform:
upgrade_platform: Checking input /var/tmp/tmp.WjGubcyRZHjunos_cli_upg/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz ...
upgrade_platform: Input package /var/tmp/tmp.WjGubcyRZHjunos_cli_upg/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz is valid.
Secure Boot is enforced.
ALLOW:usr/secureboot/grub/BOOTX64.EFI
ALLOW:boot/bzImage-intel-x86-64.bin
ALLOW:boot/initramfs.cpio.gz
Setting up Junos host applications for installation ...
Current junos instance is 0
Installing Host OS ...
upgrade_platform: -------------------
upgrade_platform: Parameters passed:
upgrade_platform: silent=0
upgrade_platform: package=/var/tmp/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz
upgrade_platform: clean install=0
upgrade_platform: on primary   =0
upgrade_platform: clean upgrade=0
upgrade_platform: Need reboot after staging=0
upgrade_platform: -------------------
upgrade_platform:
upgrade_platform: Checking input /var/tmp/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz ...
upgrade_platform: Input package /var/tmp/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz is valid.
Secure Boot is enforced.
ALLOW:usr/secureboot/grub/BOOTX64.EFI
ALLOW:boot/bzImage-intel-x86-64.bin
ALLOW:boot/initramfs.cpio.gz
upgrade_platform: Backing up boot assets..
bzImage-intel-x86-64.bin: OK
bzImage-intel-x86-64.bin.psig: OK
initramfs.cpio.gz: OK
initramfs.cpio.gz.psig: OK
version.txt: OK
upgrade_platform: Checksum verified and OK...
/boot
upgrade_platform: Backup completed
upgrade_platform: Staging the upgrade package - /var/tmp/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz..
bzImage-intel-x86-64.bin: OK
bzImage-intel-x86-64.bin.psig: OK
initramfs.cpio.gz: OK
initramfs.cpio.gz.psig: OK
version.txt: OK
upgrade_platform: Checksum verified and OK...
upgrade_platform: Staging of /var/tmp/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz completed
upgrade_platform: System need *REBOOT* to complete the upgrade
upgrade_platform: Run upgrade_platform with option -r | --rollback to rollback the upgrade

Host OS upgrade staged. Reboot the system to complete installation!
08:58 installing software on VC member: 0 ... please be patient ...
09:01 software pkgadd package-result: 0
Output: 
Verified jinstall-host-ex-4300mp-x86-64-21.4R3-S4.18-secure-signed signed by PackageProductionECP256_2023 method ECDSA256+SHA256
Pushing Junos image package to the host...
Installing /var/tmp/install-media-ex-4300mp-junos-21.4R3-S4.18-secure.tgz
Extracting the package ...

============================================
Host OS upgrade is FORCED
Current Host kernel version : 3.14.52-rt50-WR7.0.0.9_ovp
Package Host kernel version : 3.14.52-rt50-WR7.0.0.9_ovp
Current Host version        : 3.1.0
Package Host version        : 3.1.0
Min host version required for applications: 3.0.0
============================================

Validate linux image...
upgrade_platform: -------------------
upgrade_platform: Parameters passed:
upgrade_platform: silent=0
upgrade_platform: package=/var/tmp/tmp.AROXPZvP0Pjunos_cli_upg/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz
upgrade_platform: clean install=0
upgrade_platform: on primary   =0
upgrade_platform: clean upgrade=0
upgrade_platform: Need reboot after staging=1
upgrade_platform: -------------------
upgrade_platform: 
upgrade_platform: Checking input /var/tmp/tmp.AROXPZvP0Pjunos_cli_upg/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz ... 
upgrade_platform: Input package /var/tmp/tmp.AROXPZvP0Pjunos_cli_upg/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz is valid.
Secure Boot is enforced.
ALLOW:usr/secureboot/grub/BOOTX64.EFI
ALLOW:boot/bzImage-intel-x86-64.bin
ALLOW:boot/initramfs.cpio.gz
Setting up Junos host applications for installation ...
Current junos instance is 0
Installing Host OS ...
upgrade_platform: -------------------
upgrade_platform: Parameters passed:
upgrade_platform: silent=0
upgrade_platform: package=/var/tmp/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz
upgrade_platform: clean install=0
upgrade_platform: on primary   =0
upgrade_platform: clean upgrade=0
upgrade_platform: Need reboot after staging=0
upgrade_platform: -------------------
upgrade_platform: 
upgrade_platform: Checking input /var/tmp/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz ... 
upgrade_platform: Input package /var/tmp/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz is valid.
Secure Boot is enforced.
ALLOW:usr/secureboot/grub/BOOTX64.EFI
ALLOW:boot/bzImage-intel-x86-64.bin
ALLOW:boot/initramfs.cpio.gz
upgrade_platform: Backing up boot assets..
bzImage-intel-x86-64.bin: OK
bzImage-intel-x86-64.bin.psig: OK
initramfs.cpio.gz: OK
initramfs.cpio.gz.psig: OK
version.txt: OK
upgrade_platform: Checksum verified and OK...
/boot
upgrade_platform: Backup completed
upgrade_platform: Staging the upgrade package - /var/tmp/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz..
bzImage-intel-x86-64.bin: OK
bzImage-intel-x86-64.bin.psig: OK
initramfs.cpio.gz: OK
initramfs.cpio.gz.psig: OK
version.txt: OK
upgrade_platform: Checksum verified and OK...
upgrade_platform: Staging of /var/tmp/jinstall-ex-4300mp-junos-21.4R3-S4.18-secure-linux.tgz completed
upgrade_platform: System need *REBOOT* to complete the upgrade
upgrade_platform: Run upgrade_platform with option -r | --rollback to rollback the upgrade

Host OS upgrade staged. Reboot the system to complete installation!
```
## fireblade.ii
v1\
Introducing fireblade.ii for inventory of inactive interfaces on Juniper switches EX4300 and EX2300. In some network operations such an inventory would be also referred as port capacity.
### Key Features:
1) Up to 100 simultenious sessions at a round;
2) Uses an agentm slax script 'portusage.slax' intalled on Juniper hosts as agent.
3) Filter quateria: an interface's last flap dated back to last system boot date;
4) Creates log directory 'inactive.interface.yyyy-mm-dd' at ~/logs/ for all generated files below;
5) Generates summary log file named 'summary.log' with the collective inventory statistics;
6) Prints on screen the collective inventory statistics, and error if fireblade.ii fails to connect to any hosts;
7) Generates verbose inventory files for all connected host. Each file contains a list of inactive interfaces that meet the quateria, and the raw data from 
```
usage: fireblade.ii.py [-h] (-H HOSTS [HOSTS ...] | -l FILE)

Fireblade.ii for inventory of inactive interfaces on Juniper switches

optional arguments:
  -h, --help            show this help message and exit
  -H HOSTS [HOSTS ...], --hosts HOSTS [HOSTS ...]
                        hosts' FQDN in format of 'host1' 'host2'...single and
                        double quote function the same.
  -l FILE, --host_list FILE
                        Direcotry to a list of hosts.
```
### Exampple
```
$ python3 netauto/fireblade.ii.py -H
Username: M.Schumacher
Password: formula1champion

Fireblade.ii is inquiring the inventory of inactive interfaces on below chassis.
An summary for all chassis and their respective inventory files will be saved in directory:
./logs/inactive.interface.2023-11-10

Hostname,Number of alive days,Number of members,Number of MPs,Number of Ps,Number of total interfaces,Number of inactive interfaces,Percentage of inactive interfaces
host1,23w0d,1,0,0,12,9,75%
host2,45w6d,3,0,3,144,34,24%
host3,1w4d,10,0,10,480,255,53%
$
$ ls -l ~/logs/inactive.interface.2023-11-10/
total 52
-rw-rw-r--. 1 M.Schumacher formula1  1630 Nov 10 13:39 host1.ii.list.log
-rw-rw-r--. 1 M.Schumacher formula1  6769 Nov 10 13:39 host2.ii.list.log
-rw-rw-r--. 1 M.Schumacher formula1   339 Nov 10 13:40 summary.log
-rw-rw-r--. 1 M.Schumacher formula1 35258 Nov 10 13:40 host3.ii.list.log
$ cat ~/logs/inactive.interface.2023-11-10/host1.ii.list.log
---inventory of inactive interfaces---
 ge-0/0/0
 ge-0/0/1
 ge-0/0/2
 ge-0/0/3
 ge-0/0/4
 ge-0/0/5
 ge-0/0/6
 ge-0/0/7
 ge-0/0/9

---portusage raw data---
['Type      \t Interface       \t Status    \t Last Flapped         \t Interface Description\r', 'physical  \t vme             \t up/down   \t Never                \t \r', 'physical  \t ge-0/0/11       \t up/down   \t 2023-10-06 17:13:12 PDT (4w6d 21:50 ago)\t \r', 'physical  \t ge-0/0/10       \t up/down   \t 2023-10-06 17:13:10 PDT (4w6d 21:50 ago)\t \r', 'physical  \t ge-0/0/8        \t up/down   \t 2023-09-29 12:55:59 PDT (6w0d 02:07 ago)\t \r', 'physical  \t ge-0/0/0        \t up/down   \t 2023-06-02 07:38:20 PDT (23w0d 07:25 ago)\t \r', 'physical  \t ge-0/0/1        \t up/down   \t 2023-06-02 07:38:20 PDT (23w0d 07:25 ago)\t \r', 'physical  \t ge-0/0/2        \t up/down   \t 2023-06-02 07:38:20 PDT (23w0d 07:25 ago)\t \r', 'physical  \t ge-0/0/3        \t up/down   \t 2023-06-02 07:38:20 PDT (23w0d 07:25 ago)\t \r', 'physical  \t ge-0/0/4        \t up/down   \t 2023-06-02 07:38:20 PDT (23w0d 07:25 ago)\t \r', 'physical  \t ge-0/0/5        \t up/down   \t 2023-06-02 07:38:20 PDT (23w0d 07:25 ago)\t \r', 'physical  \t ge-0/0/6        \t up/down   \t 2023-06-02 07:38:20 PDT (23w0d 07:25 ago)\t \r', 'physical  \t ge-0/0/7        \t up/down   \t 2023-06-02 07:38:20 PDT (23w0d 07:25 ago)\t \r', 'physical  \t ge-0/0/9        \t up/down   \t 2023-06-02 07:38:20 PDT (23w0d 07:25 ago)\t \r', 'physical  \t me0             \t up/down   \t 2023-06-02 07:37:52 PDT (23w0d 07:25 ago)\t \r']
$
```

## portusage.slax
v1\
This script was developped by Erik Zhu. It is called as an agent in fireblade.ii to generate a list of interfaces that are in the status of "Down" on a Juniper network equipment. It is a script stored at directory /var/db/scripts/op/, and excutable with JUNOS command 'op'.
### Example
```
username@host> op portusage
Type             Interface               Status          Last Flapped            Interface Description
physical         vme                     up/down         Never
physical         ge-0/2/1                up/down         2023-11-06 15:46:52 PST (21:28:00 ago)
physical         ge-1/0/0                up/down         2023-10-28 12:32:57 PDT (1w3d 01:41 ago)
physical         ge-1/0/1                up/down         2023-10-28 12:32:57 PDT (1w3d 01:41 ago)
...
<output omitted>
...
physical         mge-0/0/46              up/down         2023-10-28 12:32:45 PDT (1w3d 01:42 ago)
physical         mge-0/0/47              up/down         2023-10-28 12:32:45 PDT (1w3d 01:42 ago)
physical         em0                     up/down         2023-10-28 12:31:29 PDT (1w3d 01:43 ago)
physical         em1                     up/down         2023-10-28 12:30:43 PDT (1w3d 01:44 ago)
```
## fireblade.py(legacy)
v1.2.2\
Development on this script is ceased upon the release of fireblade.mss, as the latter offers higher efficency and more features.
### Command Line Options
```
usage: fireblade.py [-h] (-H SINGLE_HOST | -l FILE) (-c COMMAND | -f FILE) [-m {show,testconfig,commit}] [-p {830,80}]

General Queries & Configuration Changes Tool

optional arguments:
  -h, --help            show this help message and exit
  -H SINGLE_HOST, --single_host SINGLE_HOST
                        FQDN of a host
  -l FILE, --hosts_list FILE
                        Direcotry to a list of hosts
  -c COMMAND, --command COMMAND
                        A cli command
  -f FILE, --cmdfile FILE
                        Directory to a cli command file.
  -m {show,testconfig,commit}, --mode {show,testconfig,commit}
                        Operation mode: Default to "show", options of "testconfig" and "commit"
  -p {830,80}, --port {830,80}
                        TCP port for NETCONF session. 830 by default otherwise 80
```
### Examples 1 - query on a single host
```
$ pythno3 ~/netauto/fireblade.py -H <hostname> -c 'show ethernet-switching table vlan-name DATA | except "ae0"'
```
### Example 2 - testing configuration on a number of selected hosts
```
$ python3 ~/netauto/fireblade.py -l ~/garage/hosts.list -f ~/garage/cli.adding.vlan.abc -m testconfig
```
### Examle 3 - apply and commit configuration changes on a number of hosts
```
$ python3 ~/netauto/fireblade.py -l ~/garage/hosts.list -f ~/garage/cli.update.firewall.xyz -m commit
```
## fireblade.rootpass
v0.4
#### Command Line Options
```
usage: fireblade.rootpass.py [-h] (-H SINGLE_HOST | -l FILE) [-t] [-p {830,80}] [-o FILE]

NETCONF session to change root password on remote Juniper hosts and log host and password pairs

optional arguments:
  -h, --help            show this help message and exit
  -H SINGLE_HOST, --single_host SINGLE_HOST
                        FQDN of a host
  -l FILE, --hosts_list FILE
                        direcotry of a host list
  -t, --testride        discard configuration change
  -p {830,80}, --port {830,80}
                        TCP port for NETCONF session. Script uses 830 by default if this option is not set
  -o FILE, --output FILE
                        directory to output file
```
#### Dependency
Python3 standard modules passlib is required. Intall with pip:
```
$ pip install passlib
```
## fireblade.hardware.probe
v1.0
#### Command Line Options
```
usage: fireblade.hardware.probe.py [-h] [-l FILE] [-o FILE]

NETCONF management session to fetch Juniper hardware information. hostname and model in v1.0

optional arguments:
  -h, --help            show this help message and exit
  -l FILE, --hosts_list FILE
                        a host list
  -o FILE, --output FILE
                        output dictionary
```
