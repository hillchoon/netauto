# fireblade.mss.py v1.2 - added feature to skip the host and its commands in host-command table file if the host is commented out

import sys
import argparse
import os
from getpass import getpass
from jnpr.junos import Device
from jnpr.junos.exception import *
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos.utils.config import Config
from utils import formatter, fireblade_hw
import concurrent.futures

# get and process command line options
def getArgs():

    parser = argparse.ArgumentParser(
        description = 'General Queries & Configuration Changes Tool',
        formatter_class=argparse.RawTextHelpFormatter
        )
    
    # group arg_host: -t / --host_cmd_table is part of this group.
    # The parser will automatically enforce that exactly one of -H, -l, or -t is provided.
    arg_host = parser.add_mutually_exclusive_group(required=True)
    arg_host.add_argument('-H', '--hosts', nargs='+', 
        help='hosts\' FQDN in format of \'host1\' \'host2\'...single and double quote function the same.')
    arg_host.add_argument('-l', '--host_list', metavar="FILE", help='Direcotry to a list of hosts.')
    arg_host.add_argument('-t', '--host_cmd_table', metavar="FILE", help='Directory to a consolidated table of target hosts \nand their differentiated execution commands.')

    # group arg_cmd
    arg_cmd = parser.add_mutually_exclusive_group()
    arg_cmd.add_argument('-c', '--commands', nargs='+', 
        help="command(s) in format of 'command1' 'command2'...\nsingle quote is suggested to save double quote for JUNOS commands")
    arg_cmd.add_argument('-f', '--cmdfile', metavar="FILE", help='Directory to a cli command file.')

    # arg 'mode'
    parser.add_argument('-m', '--mode', choices=['show','testride', 'comconf', 'commit', 'intdesc'], default='show', 
        help='Operation mode: Default to "show". Other choices are:\n' + 
        '"testride" for testing configuration;\n' + 
        '"comconf" for "commit confirm" with input minutes;\n' + 
        '"commit" as what it is;\n' +
        '"intdesc" for "update interface description" with specific input VLAN names')

    # arg 'campus'
    parser.add_argument('-p', '--campus', choices=['bby', 'sry', 'van'],
        help='Campus: self-explanatory. All campuses are covered if no option of campus is provided.')

    # arg 'role'
    parser.add_argument('-r', '--role', default='all', 
        choices=['all', 'core', 'edge', 'ext', 'mgmt'], 
        help='Chassis role: Default to "all" for all chassis. Other choices are: ' +
        '\n"core" for CORE switches;' + 
        '\n"edge" for EDGE switches;' + 
        '\n"ext" for EXTENSION switches; ' + 
        'and "mgmt" for MANAGEMENT network.')

    # arg 'model'
    parser.add_argument('-d', '--model', default='all', choices=['all', 'c', 'p', 'mp', 'm'], 
        help='Chassis model: Default to "all" for all models,other choices are:' + 
        '\n"c" for "EX2300-C-12P",' + 
        '\n"p" for "EX4300-48P",' + 
        '\n"mp" for "EX4300-48MP",' +
        '\nand "m" for manual input.')

    parser.add_argument('-s', '--silencer', action="store_false",
        help='Silence the output for mismatch hosts.')

    # start taking and processing args
    args = parser.parse_args()

    # 1. Dependency / Exclusion Validation
    if args.host_cmd_table and (args.commands or args.cmdfile):
        parser.error("Only one of --host_cmd_table or command arguments (--commands/--cmdfile) is allowed.")

    # 2. File Path Availability Validation
    if args.host_list and not os.path.isfile(args.host_list):
        parser.error(f"Host list file does not exist: {args.host_list}")
        
    if args.cmdfile and not os.path.isfile(args.cmdfile):
        parser.error(f"Command file does not exist: {args.cmdfile}")
        
    if args.host_cmd_table and not os.path.isfile(args.host_cmd_table):
        parser.error(f"Host-command table file does not exist: {args.host_cmd_table}")

    # model resolution
    model = 'all' if args.model == 'all' else 'EX4300-48P' if args.model == 'p' else 'EX4300-48MP' if args.model == 'mp' else 'EX2300-C-12P' if args.model == 'c' else input("Please key in specific model: ") if args.model == 'm' else None
    
    return args.hosts, args.host_list, args.host_cmd_table, args.commands, args.cmdfile, args.mode, model, args.role, args.campus, args.silencer

# process credential
def getCredential():
    credential = ['','']
    uname = input('Username: ')
    credential[0] = uname.strip()
    passwd = getpass('Password: ')
    credential[1] = passwd
    return credential

# parse simple list files (for hosts or commands)
def list_parser(filepath):
    with open(filepath, "r") as fo:
        return [line.strip() for line in fo.readlines() if line.strip() and not line.startswith('#')]

# parse host-command table files
def table_parser(filepath):
    host_cmd_table = {}
    current_host = None
    
    with open(filepath, 'r') as fo:
        for line in fo:
            line = line.strip()
            if not line:
                continue
            
            # Detect comments
            is_comment = line.startswith('#') or line.startswith(';')
            clean_line = line[1:].strip() if is_comment else line
            
            # Check if this line (or commented line) is a header block [hostname]
            if clean_line.startswith('[') and clean_line.endswith(']'):
                hostname = clean_line[1:-1].strip()
                # If the header is commented out, or the hostname starts with '#', disable tracking
                if is_comment or hostname.startswith('#'):
                    current_host = None
                else:
                    current_host = hostname
                    if current_host not in host_cmd_table:
                        host_cmd_table[current_host] = []
                continue
            
            # Skip regular comment lines
            if is_comment:
                continue
                
            elif current_host is not None:
                host_cmd_table[current_host].append(line)
                
    return host_cmd_table

# funciton 'convertreplace' generate 
def convertreplace(dev, old_pattern, new_pattern):

    # generate command to get matched lines
    command = [f"show configuration | display set | match {old_pattern}"]
    # get matched lines
    matched_config_lines = inquiry(dev, command).splitlines()
    
    # generate command sets equipvalent to 'replace pattern with'
    commands = []
    for line in matched_config_lines:
        commands.append(line.replace('set','delete').strip())
        commands.append(line.replace(old_pattern, new_pattern).strip())

    return commands

# function 'inquiry' to execute show commands
def inquiry(dev, commands):
    host_shell = StartShell(dev)
    print_out = ''
    try:
        host_shell.open()
        # execute show commands
        for command in commands:
            print_out += f"\033[1;34mOutput for command:\033[0m {command}:\n\n"
            cli_output = host_shell.run(f"cli -c '{command} | no-more'")[1]
            trimed_output = formatter.pop_first_last_lines(cli_output)

            # reassemble output
            for line in trimed_output:
                print_out += line + "\n"
            print_out += "\n"
    finally:
        try:
            host_shell.close()
        except Exception:
            pass
    return print_out

# funciton 'config_change' to implement changes
def config_change(dev,commands,mode,time):
    print_out = ''
    with Config(dev, mode='exclusive') as cu:
    # excute commands
        for command in commands:
            cu.load(command, format='set', ignore_warning=True)
        diff = cu.diff()
        print_out += f'{diff}\n' if len(commands) != 0 else f'{cu.diff(rb_id=1)}\n' if len(commands) == 0 else ''
        try:
            cu.commit_check(timeout=600)
            print_out += '\033[32m' + 'Changes passed commit check.' + '\033[0m\n'
            if mode == 'commit':
                cu.commit(ignore_warning=True, timeout=600)
                print_out += '\033[32m' + 'Changes committed.' + '\033[0m\n'
            elif mode == 'comconf':
                cu.commit(ignore_warning=True, timeout=600, confirm=time)
                print_out += '\033[93;1m' + f'Changes committed and will be rolled back in {time} minutes unless confirmed ' + '\033[0m\n'
            else:
                cu.rollback()
                print_out += '\033[93;1m' + 'Changes rolled back.' + '\033[0m\n'
        except CommitError as err:
            cu.rollback()
            print_out += f'\033[31mError\033[0m in commit check, rolled back with {err.message}'
        return print_out

# netconf session
def ncsession(host, campus, model, role, commands, mode, commit_mode, time, uname, passwd, si, vlan, print_host_cmds=False):

    try:
        with Device(host=host, user=uname, password=passwd) as dev:

            # where it starts for a host
            print_out = f"\033[1;93m----------------------------------------------------------------------------\033[0m\nHost: {host}\n"
            
            # Print host-specific commands if using a host_cmd_table_file
            if print_host_cmds:
                print_out += f"commands: \n{commands}\n"

            # on/off switch of campus, role and model
            # campus
            camp = fireblade_hw.campus(dev)
            if campus is not None and campus != camp:
                print_out += f"\nThis host is on campus {camp.upper()}, campus mismatched, skipping"
                print (print_out) if si else None
                return

            # role
            r = fireblade_hw.role(dev)
            if role != 'all' and role != r:
                print_out += f"\nThis host is a '{r.upper()}' switch, chassis role mismatched, skipping."
                print (print_out) if si else None
                return

            # model
            m = fireblade_hw.model(dev)
            if model != 'all' and model != m:
                print_out += f"\nThis host is an '{m.upper()}' chassis, model mismatched, skipping."
                print (print_out) if si else None
                return
            
            # mode dictates
            if mode == 'show':  # commands to make inquiry
                print (print_out + f'\n{inquiry(dev,commands)}')

            elif mode == 'intdesc': # update interface description per its vlan
                
                interfaces = []

                # query list of interfaces that are assigned with the vlan
                outputs = inquiry(dev,['show configuration interfaces | display set | match ' + f'{vlan}'])
                for item in outputs.splitlines():
                    interfaces.append(item.split()[2])

                # remove trunked ports from interfaces
                outputs = inquiry(dev,['show configuration interfaces | display set | match trunk'])
                for item in outputs.splitlines():
                    trunk_interface = item.split()[2]
                    interfaces.remove(trunk_interface) if trunk_interface in interfaces else None
                
                # populate commands to update interface description
                commands = []
                for item in interfaces:
                    commands.append('set interfaces ' + f'{item}' + ' description ' + f'{vlan}')

                # call function 'config_change' to implement the interface description update
                print (print_out + f'\n{config_change(dev,commands,commit_mode,time)}')

            else:   # commands to make configuration changes
                # sort out commands to comply with Juniper RPC
                sorted_commands = []
                for command in commands:
                    command_split = command.split()
                    if command_split[0] == 'replace':
                        # go convertreplace
                        replace_pattern_commands = convertreplace(dev, command_split[2], command_split[4])
                        sorted_commands += replace_pattern_commands
                    else:
                        sorted_commands.append(command)

                # call function 'config_change' to implement the sorted configuration change commands
                print (print_out + f'\n{config_change(dev,sorted_commands,mode,time)}')

    except ConnectError as err:
        print(f"Cannot connect to device: {err}")
    except ConnectAuthError as err:
        print(f"Cannot authenticate to device: {err}")
    except ConnectTimeoutError as err:
        print(f"Connection to device timed out: {err}")
    except ConnectRefusedError as err:
        print(f"Connection to device was refused: {err}, please check NETCONF configuration")
    except RpcError as err:
        print(f"RPC error: {err}")

def main():

    # command line options
    try:
        args = getArgs()
        hosts = args[0]
        host_list = args[1]
        host_cmd_table_file = args[2]
        commands = args[3]
        cmdfile = args[4]
        mode = args[5]
        model = args[6]
        role = args[7]
        campus = args[8]
        silencer = args[9]
    except argparse.ArgumentError as err:
        print(f"Error: {err}")
        return

    # Resolve hosts and host_cmd_table
    if host_cmd_table_file:
        host_cmd_table = table_parser(host_cmd_table_file)
        hosts = list(host_cmd_table.keys())
    else:
        if host_list:
            hosts = list_parser(host_list)
        
        # Resolve commands list if using traditional input
        if cmdfile:
            commands = list_parser(cmdfile)
        elif not commands:
            commands = []
            
        host_cmd_table = {host: commands for host in hosts}

    vlan_name = input("VLAN NAME of interest to change interface description: ") if mode == 'intdesc' else ''
    commit_mode = input("Immediate commmit ('commit') or commit confirm ('comconf'): ") if mode == 'intdesc' else mode
    time = input("Minutes to confirm configuration change: ") if commit_mode == 'comconf' else ''

    # credential
    credential = getCredential()
    uname = credential[0]
    passwd = credential[1]

    # Print summary globally BEFORE execution ONLY IF not using a command table file
    if not host_cmd_table_file:
        print(f"commands: \n{commands}")

    # run commands on each host in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [
            executor.submit(
                ncsession, 
                host, 
                campus, 
                model, 
                role, 
                host_cmd_table[host], 
                mode, 
                commit_mode, 
                time, 
                uname, 
                passwd, 
                silencer, 
                vlan_name,
                bool(host_cmd_table_file)  # print_host_cmds flag
            ) 
            for host in hosts
        ]
        concurrent.futures.wait(futures)

        for future in futures:
            try:
                result = future.result()
                if result:
                    print (f'Good result is:{result}')

            except Exception as err:
                print (f'An error occurred: {err}')
#        print (futures)

    # ... (keep the existing code for summarizing counters, if needed)

if __name__ == '__main__':
    main()
