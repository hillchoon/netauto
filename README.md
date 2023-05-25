# Fireblade Netauto

A Juniper Network Operations & Management Toolkit

## fireblade.ms.py
v0.82\
It is happening, **simultaneously**! \
ms is short for multiple sessions. With current setting, **fireblade.ms.py** initiates 50 sessions simultaneously from management host to managed hosts at a time.\
See output below from '-h' for command line options.

#### Command Line Options
```
usage: fireblade.mss.py [-h] (-H HOSTS [HOSTS ...] | -l FILE)
                        (-c COMMANDS [COMMANDS ...] | -f FILE)
                        [-m {show,testconfig,commit}] [-d {g,p,mp}]
                        [-r {core,edge,dc,ext,mgmt}] [-p {bby,sry,van}]

General Queries & Configuration Changes Tool

optional arguments:
  -h, --help            show this help message and exit
  -H HOSTS [HOSTS ...], --hosts HOSTS [HOSTS ...]
                        hosts' FQDN in format of 'host1' 'host2'...single and
                        double quote function the same
  -l FILE, --host_list FILE
                        Direcotry to a list of hosts
  -c COMMANDS [COMMANDS ...], --commands COMMANDS [COMMANDS ...]
                        command(s) in format of "command 1" "command
                        2"...single and double quote function the same
  -f FILE, --cmdfile FILE
                        Directory to a cli command file.
  -m {show,testconfig,commit}, --mode {show,testconfig,commit}
                        Operation mode: Default to "show", options of
                        "testconfig" and "commit"
  -d {g,p,mp}, --model {g,p,mp}
                        Chassis model: This option is only needed when
                        operation mode is "testconfig" or "commit". Default to
                        "g" for "general" when proposing changes are
                        irrelevant to chassis model,other choices are "p" for
                        "EX4300-48P" and "mp" for "EX4300-48MP"
  -r {core,edge,dc,ext,mgmt}, --role {core,edge,dc,ext,mgmt}
                        Chassis role: This option is only needed when
                        operation mode is "testconfig" or "commit". Default to
                        "edge" for regular edge switches. Other choices are
                        "core", "ext" for extension switches, "dc" for data
                        centre switches, and "mgmt" for management switches.
  -p {bby,sry,van}, --campus {bby,sry,van}
                        Campus: self-explanatory

```

## fireblade.py
v1.2.2
#### Command Line Options
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
#### Dependency
```
$ pip install junos-eznc
```
#### Examples 1 - query on a single host
```
$ pythno3 ~/netauto/fireblade.py -H <hostname> -c 'show ethernet-switching table vlan-name DATA | except "ae0"'
```
#### Example 2 - testing configuration on a number of selected hosts
```
$ python3 ~/netauto/fireblade.py -l ~/garage/hosts.list -f ~/garage/cli.adding.vlan.abc -m testconfig
```
#### Examle 3 - apply and commit configuration changes on a number of hosts
```
$ python3 ~/netauto/fireblade.py -l ~/garage/hosts.list -f ~/garage/cli.update.firewall.xyz -m commit
```
## Hidden switch in a list of host or commands
All Fireblade Netauto scripts support a hidden switch in a file of a list of hosts or commands. This switch comes in handy when you want the scripts to toggle some of the hosts or commands without having to delete them. To do that, a '#' shall be added at the begining of the line, see examples below:
```
$ cat ~/garage/hosts.campus.a
host1.com
host2.com
#host3.com
host4.com
$ cat ~/garage/cli.show
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
