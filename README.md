# Fireblade Netauto
A Juniper Network Operations & Management Toolkit

**fireblade.py**
<br>
v1.2<br>
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

Dependency: junos-eznc
$ pip install junos-eznc

```

**fireblade.rootpass.py**<br>
v0.4<br>

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

Dependency: Python3 standard modules passlib & secrets are required. Intall with pip:

$ pip install passlib
```

**fireblade.hardware.probe.py**<br>
v1.0<br>
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
