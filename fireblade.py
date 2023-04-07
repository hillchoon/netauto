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

	parser = argparse.ArgumentParser(description = 'General Queries & Configuration Changes Tool')
	
	# group arg_host 
	arg_host = parser.add_mutually_exclusive_group(required=True)
	arg_host.add_argument('-H', '--single_host', type=str, help='FQDN of a host')
	arg_host.add_argument('-l', '--hosts_list', metavar="FILE", help='Direcotry to a list of hosts')

	# group arg_cmd
	arg_cmd = parser.add_mutually_exclusive_group(required=True)
	arg_cmd.add_argument('-c', '--command', type=str, help='A cli command')
	arg_cmd.add_argument('-f', '--cmdfile', metavar="FILE", help='Directory to a cli command file.')

	# option 'mode'
	parser.add_argument('-m', '--mode', choices=['show','testconfig', 'commit'], default='show', 
		help='Operation mode: Default to "show", options of "testconfig" and "commit"')

	# option 'port' for NETCONF
	parser.add_argument('-p', '--port', choices = ['830', '80'], default = '830', 
		help='TCP port for NETCONF session. 830 by default otherwise 80')

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
	except argparse.ArgumentError as err:
		print(f"Error: {err}")
		return

	# credential
	credential = getCredential()
	uname = credential[0]
	passwd = credential[1]
	print (commands)

	# session counters
	cnt_total = hosts.length()
	cnt_connecterr,	cnt_autherr, cnt_timeout, cnt_refuse, cnt_rpcerr = [0,0,0,0,0]

	# configuration counters
	if mode != 'show':
		cnt_commit, cnt_rollback, cnt_commiterr, cnt_nodiff = [0,0,0,0]

	# run commands on each host
	for host in hosts:
		print ('\033[1;34m------------------------------------------------\033[0m')
		print ('HOST: ' + host)
		try:
			with netconf(host, uname, passwd, port) as dev:

				# mode dictates
				if mode == 'show':
					host_shell = StartShell(dev)
					host_shell.open()

					# excute commands
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
					with Config(dev, mode='exclusive') as cu:

						# excute commands
						for command in commands:
							cu.load(command,format='set',ignore_warning=True)

						if cu.diff() != None:
							print (cu.diff())

							try:
								cu.commit_check()
								print ('\033[32m' + 'Changes passed commit check.' + '\033[0m')

								if mode == 'commit':
									cu.commit(ignore_warning=True,timeout=600)
									cnt_commit += 1
									print ('\033[32m' + 'Changes committed.' + '\033[0m')
								else:
									cu.rollback()
									cnt_rollback += 1
									print ('\033[93;1m' + 'Changes rolled back.' + '\033[0m')

							except CommitError as err:
								cu.rollback()
								cnt_commiterr += 1
								print ('\033[31mError\033[0m in commit check, rolled back with ',err.message)
						else:
							cnt_nodiff += 1
							print ('No differences found.')

		except ConnectError as err:
			cnt_connecterr += 1
			print(f"Cannot connect to device: {err}")
			continue
		except ConnectAuthError as err:
			cnt_autherr += 1
			print(f"Cannot authenticate to device: {err}")
			continue
		except ConnectTimeoutError as err:
			cnt_timeout += 1
			print(f"Connection to device timed out: {err}")
			continue
		except ConnectRefusedError as err:
			cnt_refuse += 1
			print(f"Connection to device was refused: {err}, please check NETCONF configuration")
			continue
		except RpcError as err:
			cnt_rpcerr += 1
			print(f"RPC error: {err}")
			continue

	# summarize counters
	cnt_checkered = cnt_total - cnt_autherr - cnt_connecterr - cnt_timeout - cnt_refuse - cnt_rpcerr
	print ("Session Counter Summary")
	print (f"Total Number of Sessions:				{cnt_total}")
	print (f"Connected Sessions:					{cnt_checkered}")
	print (f"Connection Error Sessions:				{cnt_connecterr}")
	print (f"Authentication Error Sessions:			{cnt_autherr}")
	print (f"Timeout Sessions:						{cnt_timeout}")
	print (f"Connection Refused Sessions:			{cnt_refuse}")
	print (f"RPC Error Sessions:					{cnt_rpcerr}\n")
	
	if mode != 'show':
		print ("Configuration Change Summary")
		print (f"Total Number of Change Sessions:		{cnt_total}")
		print (f"Committed Sessions:					{cnt_commit}")
		print (f"Rolled Back Sessions:					{cnt_rollback}")
		print (f"Commit Error Sessions:					{cnt_commiterr}")
		print (f"No Difference in Change:				{cnt_nodiff}")

if __name__ == '__main__':
	main()