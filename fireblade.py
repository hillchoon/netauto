import sys
import argparse
from getpass import getpass
from jnpr.junos import Device
from jnpr.junos.exception import *
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos.utils.config import Config
from utils import formatter

# get and process input options
def getArgs():

	parser = argparse.ArgumentParser(description = 'Fireblade management tool on Juniper Devices')
	
	# group arg_host 
	arg_host = parser.add_mutually_exclusive_group(required=True)
	arg_host.add_argument('-H', '--single_host', type=str, help='FQDN of a host')
	arg_host.add_argument('-l', '--hosts_list', metavar="FILE", help='direcotry of a host list')

	# group arg_cmd
	arg_cmd = parser.add_mutually_exclusive_group(required=True)
	arg_cmd.add_argument('-c', '--command', type=str, help='a cli command')
	arg_cmd.add_argument('-f', '--cmdfile', metavar="FILE", help='directory to a command file.'
		+ 'when option "-d" is not set, this command file will run on all hosts,'
		+ 'otherwise will run on EX4300-48P hosts')

	# option 'mode'
	parser.add_argument('-m', '--mode', choices=['show','testconfig', 'config'], default='show', 
		help='command mode: "show(default)", "testconfig" or "config"')

	# option 'port' for NETCONF
	parser.add_argument('-p', '--port', choices = ['830', '80'], default = '830', 
		help='TCP port for NETCONF session. Script uses 830 by default if port is not set')

	# take available options
	args = parser.parse_args()

	# process group arg_host
	hosts = []
	if args.hosts_list and args.single_host:
		parser.error("Only one of these two options --hosts_list or --single_host is allowed")
	elif args.hosts_list is None:
		hosts.append(args.single_host.strip())
	else:
		with open(f"{args.hosts_list}", "r") as fo:
			hosts = [line.strip() for line in fo.readlines() if not line.startswith('#')]

	# process group arg_cmd
	commands = []
	if args.cmdfile and args.command:
		parser.error("Only one of these two options --cmdfile or --command is allowed")
	elif args.cmdfile is None:
		commands.append(args.command.strip())
	else:
		with open(f"{args.cmdfile}", "r") as fo:
			commands = [line.strip() for line in fo.readlines() if not line.startswith('#')]

	return hosts, commands, args.mode, args.port

# process credential
def getCredential():
	credential = ['','']
	uname = input('Username: ')
	credential[0] = uname.strip()
	passwd = getpass('Password: ')
	credential[1] = passwd
	return credential

# handle netconf session
def netconf(host_name, username, password, port):
	dev = Device(host=host_name, user=username, password=password, port=port)
	dev.open()
	return dev

def main():

	# command line options
	try:
		args = getArgs()
		hosts = args[0]
		commands = args[1]
		mode = args[2]
		port = args[3]
	except argparse.ArgumentError as e:
		print(f"Error: {e}")
		return

	# credential
	credential = getCredential()
	uname = credential[0]
	passwd = credential[1]
	print (commands)

	# run commands on each host
	for host in hosts:
		print ('------------------------------------------------')
		print ('HOST: ' + host)
		try:
			with netconf(host, uname, passwd, port) as dev:
				if mode == 'show':
					host_shell = StartShell(dev)
					host_shell.open()
					for command in commands:
						command += ' | no-more'
						cli_output = host_shell.run('cli -c "' + command.strip() + '"')[1]
						trimed_output = formatter.remove_first_last_lines(cli_output)
						if trimed_output == ['FALSE']:
							print ('Output of command ' + '"' + command + '"' + ' on host ' + host + ' is corrupted by syslog message')
							break
						for line in trimed_output:
							print (line.strip("\n"))
					host_shell.close()
				else:
					host_config = Config(dev, mode='exclusive')
					for command in commands:
						host_config.load(command,format='set',ignore_warning=True)
					if host_config.diff() != None:
						print (host_config.diff())
						if mode == 'testconfig':
							host_config.rollback()
							print ('Tested config and rolled back.')
						else:
							host_config.commit(ignore_warning=True,timeout=600)
							print ('Changes committed.')

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

if __name__ == '__main__':
	main()
