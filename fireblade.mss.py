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
        help='hosts\' FQDN in format of \'host1\' \'host2\'...single and double quote function the same')
    arg_host.add_argument('-l', '--host_list', metavar="FILE", help='Direcotry to a list of hosts')

    # group arg_cmd
    arg_cmd = parser.add_mutually_exclusive_group(required=True)
    arg_cmd.add_argument('-c', '--commands', nargs='+', 
        help='command(s) in format of "command 1" "command 2"...single and double quote function the same')
    arg_cmd.add_argument('-f', '--cmdfile', metavar="FILE", help='Directory to a cli command file.')

    # option 'mode'
    parser.add_argument('-m', '--mode', choices=['show','testconfig', 'commit'], default='show', 
        help='Operation mode: Default to "show", options of "testconfig" and "commit"')

    # option 'model'
    parser.add_argument('-d', '--model', choices=['g', 'p', 'mp'], default='general',
        help='Chassis model: This option is only needed when operation mode is "testconfig" or "commit". ' + 
        'Default to "g" for "general" when proposing changes are irrelevant to chassis model,' +
        'other choices are "p" for "EX4300-48P" and "mp" for "EX4300-48MP"')

    # option 'role'
    parser.add_argument('-r', '--role', choices=['core', 'edge', 'dc', 'ext', 'mgmt'], default='edge',
        help='Chassis role: This option is only needed when operation mode is "testconfig" or "commit". ' + 
        'Default to "edge" for regular edge switches. Other choices are "core", "ext" for extension switches, ' + 
        '"dc" for data centre switches, and "mgmt" for management switches.')

    # option 'campus'
    parser.add_argument('-p', '--campus', choices=['bby', 'sry', 'van'],
        help='Campus: self-explanatory')

    # take available options
    args = parser.parse_args()

    # process group arg_host
    hosts = []
    if args.host_list and args.hosts:
        parser.error("Only one of these two options --host_list or --hosts is allowed")
    elif args.host_list:
        with open(f"{args.host_list}", "r") as fo:
            hosts = [line.strip() for line in fo.readlines() if not line.startswith('#')]
    else:
        hosts = args.hosts

    # process group arg_cmd
    commands = []
    if args.cmdfile and args.commands:
        parser.error("Only one of these two options --cmdfile or --command is allowed")
    elif args.cmdfile:
        with open(f"{args.cmdfile}", "r") as fo:
            commands = [line.strip() for line in fo.readlines() if not line.startswith('#')]
    else:
        commands = args.commands

    return hosts, commands, args.mode, args.model, args.role, args.campus #, args.port

# process credential
def getCredential():
    credential = ['','']
    uname = input('Username: ')
    credential[0] = uname.strip()
    passwd = getpass('Password: ')
    credential[1] = passwd
    return credential

# netconf session
def ncsession(host, campus, model, role, commands, mode, uname, passwd):

    try:
        with Device(host=host, user=uname, password=passwd) as dev:

            # where a host starts
            print_out = f"\033[1;34m------------------------------------------------\033[0m\nHost: {host}\n"

            # flow control by campus
            #camp = fireblade_hw.campus(dev)
            if campus is not None and campus != fireblade_hw.campus(dev):
                print_out += f"\nThis host is not on desired campus {campus.upper()}, skipping."
                print (print_out)
                return
            
            # mode dictates
            if mode == 'show':
                host_shell = StartShell(dev)
                host_shell.open()

                # excute commands
                for command in commands:

                    cli_output = host_shell.run(f"cli -c '{command} | no-more'")[1]
                    trimed_output = formatter.pop_first_last_lines(cli_output)

                    # reassemble output
                    for line in trimed_output:
                        print_out += line + "\n"

                host_shell.close()
                print (print_out)

            else:

                # skip change on mis-matched role
                if fireblade_hw.role(dev) != role:
                    print_out += f"\nThis host is not a '{role}'' switch, skipping changes."
                    print (print_out)
                    return

                # skip change on mis-matched model
                if model == 'EX4300-48MP' and fireblade_hw.model(dev) != model:
                    print_out += "\nThis host is not in the same chassis model which changes are proposed to, skipping changes."
                    print (print_out)
                    return
                if model == 'EX4300-48P' and fireblade_hw.model(dev) == 'EX4300-48MP':
                    print_out += "\nThis host is not in the same chassis model which changes are proposed to, skipping changes."
                    print (print_out)
                    return

                # continue on matched chassis
                with Config(dev, mode='exclusive') as cu:

                    # excute commands
                    for command in commands:
                        cu.load(command, format='set', ignore_warning=True)

                    if cu.diff() != None:
                        print_out += f'{cu.diff()}\n'
                        try:
                            cu.commit_check(timeout=600)
                            print_out += '\033[32m' + 'Changes passed commit check.' + '\033[0m\n'
                            if mode == 'commit':
                                cu.commit(ignore_warning=True, timeout=600)
                                print_out += '\033[32m' + 'Changes committed.' + '\033[0m\n'
                            else:
                                cu.rollback()
                                print_out += '\033[93;1m' + 'Changes rolled back.' + '\033[0m\n'
                        except CommitError as err:
                            cu.rollback()
                            print_out += f'\033[31mError\033[0m in commit check, rolled back with {err.message}'
                    else:
                        print('No differences found.')

                    print (print_out)

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
    except argparse.ArgumentError as err:
        print(f"Error: {err}")
        return

    # credential
    credential = getCredential()
    uname = credential[0]
    passwd = credential[1]
    print (commands)

    chassis_model = 'general' if model == 'g' else 'EX4300-48P' if model == 'p' else 'EX4300-48MP' if model == 'mp' else None

    # run commands on each host in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(ncsession, host, campus, chassis_model, role, commands, mode, uname, passwd) 
        for host in hosts]
        concurrent.futures.wait(futures)

    # ... (keep the existing code for summarizing counters, if needed)

if __name__ == '__main__':
    main()
