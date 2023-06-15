# Netauto

A set of Python3 tools developed for managing and operating Juniper Network in Network Operations.

## 1. You as A User
### 1.1 A NOC User
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
### 1.2 A SUDO User
1) Installs Python3, Junos PyEZ, and other third-party libraries (listed per Netauto script if any depedency).  
```
$ pip3 install junos-eznc
```
2) Create and maintain a text list of managed network hosts, place the list in a directory to which NOC users are granted with read-only access.
## 2. Common Command Line Arguments
A common command line to launch a Netauto script is:
```
$ python3 <directory-of-a-netauto-script> <argument-of-managed-hosts> <argument-of-commands> <other-arguments>
```
**argument-of-managed-hosts**  
This argument could be:  
1) the directory to a text file of hosts' IP or FQDN. i.e. ~/garage/hosts.all, or  
2) a list of FQDN of hosts with a space in between. i.e. host1.domain.com host2.domain.com host3.domain.com  

**argument-of-commands**  
Netauto drives different features for pulling information and pushing configuration changes, therefore this arugument is for either query or configuration, not a mix of both.  
This argument could be:
1) the directory to a text file of JUNOS commands, or  
2) a list of quoted commands with a space in between. i.e. 'show system information | match "keyword"' 'show system uptime' 'show interfaces ge-0/0/0 extensive | match "error"'
## 3. fireblade.mss
v1.0\
It is happening, **simultaneously**! \
Introducing fireblade.mss for **m**ultiple **s**ession**s**.
### Key Features:
1) 50 simultaneous sessions from management server to managed hosts at a time;
2) Flexible input of multiple hosts and commands as command line arguments;
3) Filter target hosts with arguments of campus, role, chassis model;
4) Silencer to mute output for hosts that mismatch given creteria.
See details below from command line option '-h'.

### Command Line Options
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
## fireblade.py
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
## Hidden switch in a list of host or commands
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

## fireblade.rootpass.py
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
## fireblade.hardware.probe.py
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
