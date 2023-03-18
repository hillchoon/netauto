# Fireblade Netauto
Management Automation on A Juniper Network

---------------------
fireblade.rootpass.py
---------------------
```
usage: fireblade.rootpass.py [-h] (-H SINGLE_HOST | -l FILE) [-t] [-p {830,80}] [-o FILE]

NETCONF session to change root password and write hostname and new password to a file

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

pip install secrets
pip install passlib
```

