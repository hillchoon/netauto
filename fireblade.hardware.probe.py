import sys
import os
import argparse
from getpass import getpass
from jnpr.junos import Device
from jnpr.junos.exception import *

def getCredential():
	credential = ['','']
	uname = input('Username: ')
	credential[0] = uname.strip()
	passwd = getpass('Password: ')
	credential[1] = passwd
	return credential

def get_args():
	parser = argparse.ArgumentParser(description = 'NETCONF management session to fetch Juniper hardware information')
	parser.add_argument('-l', '--hosts_list', metavar="FILE", help='a host list')
	parser.add_argument('-o', '--output', metavar='FILE', help='output dictionary')
	args = parser.parse_args()
	return args

def netconf(host_name, username, password):
    dev = Device(host=host_name, user=username, password=password)
    dev.open()
    return dev

def main():
	args = get_args()
	# read host file to list hosts
	with open(f"{args.hosts_list}","r") as fo:
		hosts = [line.strip() for line in fo.readlines() if not line.startswith('#')]

	credential = getCredential()
	uname = credential[0]
	passwd = credential[1]

	# open and write hardware information to the output file
	with open(f"{args.output}",'a') as fo:
		for host in hosts:
			try:
				with netconf(host, uname, passwd) as dev:
					hostname = dev.facts['hostname']
					model = dev.facts['model']

					data = {'hostname': hostname, 'model': model}
					print (data)
					fo.write(str(data) + '\n')

			except ConnectError as err:
			    print(f"Cannot connect to device: {err}")
			    continue
			except ConnectAuthError as err:
			    print(f"Cannot authenticate to device: {err}")
			    sys.exit(1)
			except ConnectTimeoutError as err:
			    print(f"Connection to device timed out: {err}")
			    continue
			except ConnectRefusedError as err:
			    print(f"Connection to device was refused: {err}, please check NETCONF configuration")
			    continue
			except RpcError as err:
			    print(f"RPC error: {err}")
			    continue

if __name__ == '__main__':
	main()