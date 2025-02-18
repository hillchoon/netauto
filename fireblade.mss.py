import sys
import argparse
from getpass import getpass
from jnpr.junos import Device
from jnpr.junos.exception import *
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos.utils.config import Config
from utils import formatter, fireblade_hw
import concurrent.futures

# get and process command line options
def getArgs():

    parser = argparse.ArgumentParser(description = 'General Queries & Configuration Changes Tool')
    
    # group arg_host 
    arg_host = parser.add_mutually_exclusive_group(required=True)
    arg_host.add_argument('-H', '--hosts', nargs='+', 
        help='hosts\' FQDN in format of \'host1\' \'host2\'...single and double quote function the same.')
    arg_host.add_argument('-l', '--host_list', metavar="FILE", help='Direcotry to a list of hosts.')

    # group arg_cmd
    arg_cmd = parser.add_mutually_exclusive_group()
    arg_cmd.add_argument('-c', '--commands', nargs='+', 
        help='command(s) in format of "command1" "command2"...single and double quote function the same.')
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
        choices=['all', 'core', 'edge', 'dc', 'ext', 'mgmt'], 
        help='Chassis role: Default to "all" for all chassis. Other choices are: "core" for CORE switches; "edge" for EDGE switches; "ext" for EXTENSION switches; ' + 
        '"dc" for DATACENTRE switches, and "mgmt" for MANAGEMENT network.')

    # arg 'model'
    parser.add_argument('-d', '--model', default='all', choices=['all', 'c', 'p', 'mp', 'm'], 
        help='Chassis model: Default to "all" for all models,' +
        'other choices are "c" for "EX2300-C-12P", "p" for "EX4300-48P", "mp" for "EX4300-48MP",' +
        'and "m" for manual input.')

    parser.add_argument('-s', '--silencer', action="store_false",
        help='Silence the output for mismatch hosts.')

    # start taking and processing args
    args = parser.parse_args()

    # group arg_host
    hosts = []
    if args.host_list and args.hosts:
        parser.error("Only one of these two options --host_list or --hosts is allowed")
    elif args.host_list:
        with open(f"{args.host_list}", "r") as fo:
            hosts = [line.strip() for line in fo.readlines() if not line.startswith('#')]
    else:
        hosts = args.hosts

    # group arg_cmd
    commands = []
    if args.cmdfile and args.commands:
        parser.error("Only one of these two options --cmdfile or --command is allowed")
    elif args.cmdfile:
        with open(f"{args.cmdfile}", "r") as fo:
            commands = [line.strip() for line in fo.readlines() if not line.startswith('#')]
    elif args.commands:

            commands = args.commands
    else:
        commands = []

    # model
    model = 'all' if args.model == 'all' else 'EX4300-48P' if args.model == 'p' else 'EX4300-48MP' if args.model == 'mp' else 'EX2300-C-12P' if args.model == 'c' else input("Please key in specific model: ") if args.model == 'm' else None
    
    return hosts, commands, args.mode, model, args.role, args.campus, args.silencer #, args.port

# process credential
def getCredential():
    credential = ['','']
    uname = input('Username: ')
    credential[0] = uname.strip()
    passwd = getpass('Password: ')
    credential[1] = passwd
    return credential

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

# function 'inqury' to excute show commands
def inquiry(dev, commands):
    host_shell = StartShell(dev)
    host_shell.open()
    print_out = ''

    # excute show commands
    for command in commands:

        cli_output = host_shell.run(f"cli -c '{command} | no-more'")[1]
        trimed_output = formatter.pop_first_last_lines(cli_output)

        # reassemble output
        for line in trimed_output:
            print_out += line + "\n"

    host_shell.close()
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
def ncsession(host, campus, model, role, commands, mode, commit_mode, time, uname, passwd, si, vlan):

    try:
        with Device(host=host, user=uname, password=passwd) as dev:

            # where it starts for a host
            print_out = f"\033[1;34m------------------------------------------------\033[0m\nHost: {host}\n"

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
        commands = args[1]
        mode = args[2]
        model = args[3]
        role = args[4]
        campus = args[5]
        silencer = args[6]
    except argparse.ArgumentError as err:
        print(f"Error: {err}")
        return

    vlan_name = input("VLAN NAME of interest to change interface description: ") if mode == 'intdesc' else ''
    commit_mode = input("Immediate commmit ('commit') or commit confirm ('comconf'): ") if mode == 'intdesc' else mode
    time = input("Minutes to confirm configuration change: ") if commit_mode == 'comconf' else ''

    # credential
    credential = getCredential()
    uname = credential[0]
    passwd = credential[1]

    print (f"commands: \n{commands}")

    # run commands on each host in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(ncsession, host, campus, model, role, commands, mode, commit_mode, time, uname, passwd, silencer, vlan_name) 
        for host in hosts]
        concurrent.futures.wait(futures)

        for future in futures:
            try:
                result = future.result()
                if result:
                    print (f'Good result is:{result}')

            except TypeError as err:
                print (f'An error occurred: {err}')
#        print (futures)

    # ... (keep the existing code for summarizing counters, if needed)

if __name__ == '__main__':
    main()
