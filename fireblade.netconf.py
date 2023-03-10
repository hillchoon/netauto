import sys
import os
from pathlib import Path
import argparse
sys.path.append('.utils/')
from getpass import getpass
from jnpr.junos import Device
from jnpr.junos.exception import *
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos.utils.config import Config
import formatter

def get_args_in_tuple(arg_single, arg_file, argtype):
	result_list = []
	if arg_single is not None and arg_file is not None:
		print ('Both a single ' + argtype + ' and a ' + argtype + ' file are provided,')
		print ('Script can only process one of them, please retry')
		return False, result_list
	elif arg_single is None and arg_file is None:
		print ('Either a single ' + argtype + ' or a ' + argtype + ' file is needed,')
		print ('Please retry')
		return False, result_list
	elif arg_single is None:
		with open(f"{arg_file}","r") as fo:
			result_list = [line.strip() for line in fo.readlines() if not line.startswith('#')]
	else:
		result_list.append(arg_single.strip())
	return True, result_list

def getArgs():
	parser = argparse.ArgumentParser(description = 'NETCONF management session to Juniper Devices')
	arg_host = parser.add_mutually_exclusive_group(required=True)
	arg_cmd = parser.add_mutually_exclusive_group(required=True)
	arg_host.add_argument('-H', '--single_host', type=str, help='FQDN of a host')
	arg_host.add_argument('-l', '--hosts_list', metavar="FILE", help='direcotry of a host list')
	arg_cmd.add_argument('-c', '--command', type=str, help='a cli command')
	arg_cmd.add_argument('-f', '--command_file', metavar="FILE", help='directory of a command file')
	parser.add_argument('-x', '--switch', choices=['show','config'], default='show', help='function switch: "show(default)" or "config"')
	parser.add_argument('-r', '--rollback', help='rollback in switch "config"', action='store_true')
	args = parser.parse_args()

	args_hosts = get_args_in_tuple(args.single_host, args.hosts_list, "host")
	args_command = get_args_in_tuple(args.command, args.command_file, "command")
	if args_hosts[0] is True:
		hosts = args_hosts[1]
	if args_command[0] is True:
		commands =args_command[1]
#	print (args.switch)
	if args.switch not in ['config', 'show']:
		print ('Function switch "' + args.switch + '" is not defined')
		sys.exit(1)
	return hosts, commands, args.switch, args.rollback

def getCredential():
	credential = ['','']
	uname = input('Username: ')
	credential[0] = uname.strip()
	passwd = getpass('Password: ')
	credential[1] = passwd
	return credential

def netconf(host_name, username, password):
    dev = Device(host=host_name, user=username, password=password)
    dev.open()
    return dev

def main():
	args = getArgs()
	credential = getCredential()
	hosts = args[0]
	commands = args[1]
	switch = args[2]
	rollback = args[3]
	uname = credential[0]
	passwd = credential[1]
	print (commands)

	for host in hosts:
		print ('------------------------------------------------')
		print ('HOST: ' + host)
		try:
			with netconf(host, uname, passwd) as dev:
				if switch == 'show':
					host_shell = StartShell(dev)
					host_shell.open()
					for command in commands:
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
#						print ('------------------------------------------------')
#						print ('* ' + command + ':')
						host_config.load(command,format='set',ignore_warning=True)
					if host_config.diff() != None:
						print (host_config.diff())
						if rollback is True:
							host_config.rollback()
						else:
							host_config.commit(ignore_warning=True,timeout=600)

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