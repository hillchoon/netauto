import sys
import argparse
from getpass import getpass
import secrets
import string
from passlib.hash import sha512_crypt
from jnpr.junos import Device
from jnpr.junos.exception import *
from jnpr.junos.utils.config import Config

# receive and process input options
def getArgs():
	parser = argparse.ArgumentParser(description = 'NETCONF session to change root password')
	arg_host = parser.add_mutually_exclusive_group(required=True)
	arg_host.add_argument('-H', '--single_host', type=str, help='FQDN of a host')
	arg_host.add_argument('-l', '--hosts_list', metavar="FILE", help='direcotry of a host list')
	parser.add_argument('-t', '--testride', help='discard configuration change', action='store_true')
	parser.add_argument('-p', '--port', choices = ['830', '80'], default = '830', 
		help='TCP port for NETCONF session. Script uses 830 by default if this option is not set')
	parser.add_argument('-o', '--output', metavar='FILE', help='directory to output file')
	args = parser.parse_args()

	hosts = []
	if args.single_host and args.hosts_list:
		parser.error("Only one of --hosts-list or --single-host can be provided")
	elif args.single_host:
		hosts.append(args.single_host.strip())
	elif args.hosts_list:
		with open(f"{args.hosts_list}", "r") as f:
			hosts = [line.strip() for line in f.readlines() if not line.startswith('#')]
	return hosts,args.testride, args.port, args.output

# process credential
def getCredential():
	credential = ['','']
	uname = input('Username: ')
	credential[0] = uname.strip()
	passwd = getpass('Password: ')
	credential[1] = passwd
	return credential

# handle netconf session
def netconf(host_name, uname, upass, port):
    dev = Device(host=host_name, user=uname, password=upass, port=port)
    dev.open()
    return dev

def main():
	args = getArgs()
	credential = getCredential()
	hosts = args[0]
	testride = args[1]
	port = args[2]
	output = args[3]
	uname = credential[0]
	upass = credential[1]

	try:
		with open(f"{output}", "w") as f:

			for host in hosts:
				print ('------------------------------------------------')
				print ('HOST: ' + host)

				try:

					# establish netconf session
					with netconf(host, uname, upass, port) as dev:

						# generate new password 'passwd'
						dic = string.ascii_letters + string.digits + string.punctuation
						passwd = ''.join(secrets.choice(dic) for i in range(24))

						# re-generate to avoid repeated char
						unique_chars = set(passwd)
						while len(unique_chars) < len(passwd):
							passwd = ''.join(secrets.choice(dic) for i in range(24))
							unique_chars = set(passwd)

						# hash passwd
						hashed_passwd = sha512_crypt(salt=secrets.token_hex(8), rounds=65000).hash(f"{passwd}")

						# start configuration utility
						try:
							with Config(dev, mode="exclusive") as cu:

								# set new root password
								cu.load(f"set system root-authentication encrypted-password \"{hashed_passwd}\"", format="set")
								print(cu.diff())
								if testride is True:
									cu.rollback()
									print ('Rollback completed')
								else:
									cu.commit(ignore_warning=True,timeout=300)
									print ("Root password has been changed.")
									f.write(f'"hostname": "{host}", "rootpass": "{passwd}"\n')

						except ConfigLoadError as err:
							print(f"Unable to load configuration changes: {err}")
						except CommitError as err:
							print(f"Unable to commit configuration changes: {err}")
						except LockError as err:
							print(f"Unable to lock the configuration: {err}")
						except UnlockError as err:
							print(f"Unable to unlock the configuration: {err}")
						except Exception as err:
						    print(f"An unexpected error occurred: {err}")

				except ConnectError as err:
					print(f"Cannot connect to device: {err}")
					continue
				except ConnectAuthError as err:
					print(f"Cannot authenticate to device: {err}")
					continue
				except ConnectTimeoutError as err:
					print(f"Connection to device timed out: {err}")
					continue
				except ConnectRefusedError as err:
					print(f"Connection to device was refused: {err}, please check NETCONF configuration")
					continue
				except RpcError as err:
					print(f"RPC error: {err}")
					continue

	except PermissionError:
		print("Permission denied")
	except Exception as e:
		print(f"An error occurred: {e}")

if __name__ == '__main__':
	main()