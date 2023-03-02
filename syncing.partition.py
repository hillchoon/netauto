import sys
import paramiko
import time
from getpass import getpass
from netmiko import ConnectHandler, ssh_exception
from datetime import datetime
import subprocess

cl = 'carling.its.sfu.ca'
#cluser = input('Username@carling: ')
#cluser = cluser.rstrip()
#clpwd = getpass('Password@carling: ')
#sfuid = input('SFU Username: ')
#sfuid = sfuid.rstrip()
#sfupwd = getpass('SFU Password: ')

cluser = 'adamchu'
clpwd = 't\MnxEN*:pF5QSLmaP'
sfuid = 'adamch'
sfupwd = 'raknoh3Lakgao'

#read host file
fo = open("bin/hosts.mp", "r")
hosts = fo.readlines()
fo.close()

#read command file
fo = open("bin/cli.2022.05.16", "r")
cmds = fo.readlines()
fo.close()
print (cmds)

#
for remotehost in (hosts):
	try:
		# initials a ssh session to carling
		cl_session = ConnectHandler(device_type = 'linux_ssh', host = 'carling.its.sfu.ca', username = cluser, password = clpwd)
		
		remotehost=remotehost.strip() + '.managenet.sfu.ca'
		print ("---------------------------------------------------------")
		print ("HOST: ", remotehost)
		print ("---------------------------------------------------------")
	
		# approach 1 initials a ssh session from carling to remotehost
		login = [
			'ssh '+sfuid+'@'+remotehost,
			f"{sfupwd}"
		]
		network_output = cl_session.send_multiline_timing(login)
		print (network_output)

		# execute commands
		for clicommand in (cmds):
			clicommand = clicommand.strip()
			#print (clicommand)
			
			if clicommand[0] != '#':
				#start_time = datetime.now()

				if 'show p partitions' in clicommand:
					# This branch processes commands on switch member level
					pmembers = cl_session.send_command('show virtual-chassis | match "ex4300-48p"')
					print ('P Members:')
					print (pmembers)
					pointer = 0
					while pointer < int(len(pmembers)/90) :
					#	start_time = datetime.now()
						member_cmd = ['request session member ' + str(pmembers[pointer*90]), 'show system snapshot media internal local', 'exit']
					#	member_cmd = ['request session member ' + str(pmembers[pointer*90]), 'request system snapshot slice alternate local', 'exit']
						for cmd in member_cmd:
							print (cl_session.send_command(cmd, read_timeout=1200))
					#	end_time = datetime.now()
					#	print (f"Exec time for syncing on this member: {end_time - start_time}\n")
					#	#	print (network_output)
					#	#print (pmembers[pointer*90])
					#	print (cl_session.send_multiline_timing(member_cmd, read_timeout=1200))
						pointer = pointer + 1
					#	print (network_output)
					#else: print ('No ex4300-48p switch is found on ' + hname)
				
				elif 'file copy' in clicommand:
					# This branch processes file copy between remotehost and carling
					filecopy = [f"{clicommand}", f"{clpwd}"]
					#print (filecopy)
					print (cl_session.send_multiline_timing(filecopy, read_timeout=0))
				
				else:
					# This branch processes other commands
					print (cl_session.send_command(clicommand, read_timeout=1200))

				#end_time = datetime.now()
				#print (f"Exec time for command {clicommand}: {end_time - start_time}\n")

		cl_session.disconnect()
	
	except ssh_exception.NetmikoTimeoutException:
		print("Carling is not reacheable")
	except ssh_exception.NetmikoAuthenticationException:
		print("Carling Authentication fail")