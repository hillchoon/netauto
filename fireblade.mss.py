import sys
import argparse
from getpass import getpass
from jnpr.junos import Device
from jnpr.junos.exception import *
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos.utils.config import Config
from utils import formatter
import concurrent.futures

# get and process command line options
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

# legacy option 'port' for NETCONF
#    parser.add_argument('-p', '--port', choices = ['830', '80'], default = '830', 
#        help='TCP port for NETCONF session. 830 by default otherwise 80')

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

    return hosts, commands, args.mode#, args.port

# process credential
def getCredential():
    credential = ['','']
    uname = input('Username: ')
    credential[0] = uname.strip()
    passwd = getpass('Password: ')
    credential[1] = passwd
    return credential

# netconf session
def ncsession(host, commands, mode, uname, passwd):
    try:
        with Device(host=host, user=uname, password=passwd) as dev:
            print_out = f"\033[1;34m------------------------------------------------\033[0m\nHost: {host}\n"
            
            # mode dictates
            if mode == 'show':
                host_shell = StartShell(dev)
                host_shell.open()

                # excute commands
                for command in commands:

                    command += ' | no-more'
                    cli_output = host_shell.run('cli -c "' + command.strip() + '"')[1]
                    trimed_output = formatter.pop_first_last_lines(cli_output)

                    # reassemble output
                    for line in trimed_output:
                        print_out += line + "\n"

                host_shell.close()
                print (print_out)

            else:
                with Config(dev, mode='exclusive') as cu:

                    # excute commands
                    for command in commands:
                        cu.load(command, format='set', ignore_warning=True)

                    if cu.diff() != None:
                        print_out += f'{host} {cu.diff()}\n'
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
        futures = [executor.submit(ncsession, host, commands, mode, uname, passwd) 
        for host in hosts]
        concurrent.futures.wait(futures)

    # ... (keep the existing code for summarizing counters, if needed)

if __name__ == '__main__':
    main()
