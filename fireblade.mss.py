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
        help='command(s) in format of "command1" "command2"...single and double quote function the same')
    arg_cmd.add_argument('-f', '--cmdfile', metavar="FILE", help='Directory to a cli command file.')

    # option 'mode'
    parser.add_argument('-m', '--mode', choices=['show','testconfig', 'commit'], default='show', 
        help='Operation mode: Default to "show", options of "testconfig" and "commit"')

    # option 'campus'
    parser.add_argument('-p', '--campus', choices=['bby', 'sry', 'van'],
        help='Campus: self-explanatory. All campuses are covered if no option of campus is provided')

    # option 'role'
    parser.add_argument('-r', '--role', default='all', 
        choices=['all', 'core', 'edge', 'dc', 'ext', 'mgmt'], 
        help='Chassis role: Default to "all" for all chassis. Other choices are: "core" for CORE switches; "edge" for EDGE switches; "ext" for EXTENSION switches; ' + 
        '"dc" for DATACENTRE switches, and "mgmt" for MANAGEMENT network.')

    # option 'model'
    parser.add_argument('-d', '--model', default='all', choices=['all', 'c', 'p', 'mp', 'm'], 
        help='Chassis model: Default to "all" for all models,' +
        'other choices are "c" for "EX2300-C-12P", "p" for "EX4300-48P/EX2300", "mp" for "EX4300-48MP",' +
        'and "m" for manual input')

    # start of taking and processing args
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
    else:
        commands = args.commands

    # model
    model = 'all' if args.model == 'all' else 'EX4300-48P' if args.model == 'p' else 'EX4300-48MP' if args.model == 'mp' else 'EX2300-C-12P' if args.model == 'c' else input("Please key in specific model: ") if args.model == 'm' else None
    
    return hosts, commands, args.mode, model, args.role, args.campus #, args.port

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

            # where it starts for a host
            print_out = f"\033[1;34m------------------------------------------------\033[0m\nHost: {host}\n"

            # on/off switch of campus, role and model
            # campus
            camp = fireblade_hw.campus(dev)
            if campus is not None and campus != camp:
                print_out += f"\nThis host is on campus {camp.upper()}, campus mismatched, skipping"
                print (print_out)
                return

            # role
            r = fireblade_hw.role(dev)
            if role != 'all' and role != r:
                print_out += f"\nThis host is a '{r.upper()}' switch, chassis role mismatched, skipping."
                print (print_out)
                return

            # model
            m = fireblade_hw.model(dev)
            if model != 'all' and model != m:
                print_out += f"\nThis host is an '{m.upper()}' chassis, model mismatched, skipping."
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

    # run commands on each host in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(ncsession, host, campus, model, role, commands, mode, uname, passwd) 
        for host in hosts]
        concurrent.futures.wait(futures)

    # ... (keep the existing code for summarizing counters, if needed)

if __name__ == '__main__':
    main()
