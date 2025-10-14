# fireblade.vlan.flip.py is a python3 tool 
# to deploy some VLAN changes on target hosts. It
# 1. changes VLAN assignment on switch interfaces per specific rules;
# 2. (thinking...)
'''
command line option vlan_change_matrix is a text file in below format:
bby-brh7046-ext-1.managenet.sfu.ca  ge-0/0/10    DATA    NAC-UNPRIV
bby-brh7046-ext-1.managenet.sfu.ca  ge-0/0/11    DATA    NAC-UNPRIV
bby-ham1040-ext-1.managenet.sfu.ca  ge-0/0/10    DATA    NAC-UNPRIV
bby-ham1040-ext-1.managenet.sfu.ca  ge-0/0/11    DATA    NAC-UNPRIV
'''

import sys
import argparse
from lxml import etree
from collections import defaultdict
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
        description = 'Specific VLAN Change Tool',
        formatter_class=argparse.RawTextHelpFormatter
        )
    
    # arg 'vlan_change_matrix'
    parser.add_argument('-c', '--vlan_change_matrix',
        required = True,
        metavar="FILE", 
        help='A matrix file containing VLAN change info'
        )

    # arg 'mode'
    parser.add_argument('-m', '--mode',
        choices=['testride', 'commitconfirm', 'commit', 'commit-at'],
        default='testride', 
        help='Operation mode: Default to "testride". Other choices are:\n' + 
        '"commitconfirm" for "commit confirm" with input minutes;\n' + 
        '"commit" as what it is; and\n' +
        '"commit-at" for "commit at specific time" with input datetime.'
        )

    # start taking and processing args
    args = parser.parse_args()

    # vlan_change_matrix
    if args.vlan_change_matrix is None:
        parser.error('A vlan_change_matrix file is expected')
    else:
        with open(f"{args.vlan_change_matrix}","r") as fo:
            vlan_matrix = [line.strip() for line in fo.readlines() if not line.startswith('#')]
    
    return vlan_matrix, args.mode

# process credential
def getCredential():
    credential = ['','']
    uname = input('Username: ')
    credential[0] = uname.strip()
    passwd = getpass('Password: ')
    credential[1] = passwd
    return credential

"""
function 'change_cmd_gen' to generate change commands
based on provided change marix file in CLI option change_matrix
it returns a dictionary that stores lists grouped by unique host fqdn
and the commands of changing vlan on interfaces
"""
def change_cmd_gen(matrix):

    # remove duplicates from matrix
    matrix = set(matrix)

    # create a dictionary
    host_change_dict = defaultdict(list)

    for item in matrix:
        # Split the item into the four required sections.
        # It handles a mix of spaces and tabs as separators, if any.
        try:
            hostname, interface, original_vlan, new_vlan = item.split(',')
        except ValueError:
            # Skip malformed lines
            print(f"Skipping malformed line: {item}")
            continue

        # Command 1: Delete the original VLAN membership (original_vlan)
        delete_cmd = f"delete interfaces {interface} unit 0 family ethernet-switching vlan members {original_vlan}"

        # Command 2: Set the new VLAN membership (new_vlan)
        set_cmd = f"set interfaces {interface} unit 0 family ethernet-switching vlan members {new_vlan}"

        # Add both commands to the corresponding host list
        host_change_dict[hostname].append(delete_cmd)
        host_change_dict[hostname].append(set_cmd)

    return host_change_dict

# funciton 'config_change' to implement changes
def config_change(dev,commands,mode,commit_at_time,confirm_time):
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

            if mode == 'commit': # execute commit immediately
                cu.commit(ignore_warning=True, timeout=600)
                print_out += '\033[32m' + 'Changes committed.' + '\033[0m\n'

            elif mode == 'commit-at': # execute the commit-configuration RPC with at-time
                report = dev.rpc.commit_configuration(at_time=commit_at_time, timeout=1200)
                print_out += etree.tostring(report, pretty_print=True).decode()

            elif mode == 'commitconfirm': # execute the commit with a confirmation time
                cu.commit(ignore_warning=True, timeout=600, confirm=time)
                print_out += '\033[93;1m' + f'Changes committed and will be rolled back in {time} minutes unless confirmed ' + '\033[0m\n'

            else: # go by deault mode testride
                cu.rollback()
                print_out += '\033[93;1m' + 'Changes rolled back.' + '\033[0m\n'

        except CommitError as err:
            cu.rollback()
            print_out += f'\033[31mError\033[0m in commit check, rolled back with {err.message}'

        return print_out

# netconf session
def ncsession(
    host,
    uname,
    passwd,
    commands,
    mode,
    commit_at_time,
    confirm_time
    ):

    try:
        with Device(host=host, user=uname, password=passwd) as dev:

            # where it starts for a host
            print_out = f"\033[1;34m------------------------------------------------\033[0m\nHost: {host}\n"

            # call function 'config_change' to implement the sorted configuration change commands
            print_out += f'\n{config_change(dev,commands,mode,commit_at_time,confirm_time)}'

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

    return print_out

def main():

    # command line options
    try:
        args = getArgs()
        vlan_matrix = args[0]
        mode = args[1]
    except argparse.ArgumentError as err:
        print(f"Error: {err}")
        return

    commit_at_time = input('Dateime to commmit (yyyy-mm-dd hh[:mm:ss]): ') if mode == 'commit-at' else None
    confirm_time = input("Minutes to confirm configuration change: ") if mode == 'commitconfirm' else None

    # credential
    credential = getCredential()
    uname = credential[0]
    passwd = credential[1]

    # call function change_cmd_gen to generate Juniper CLI change
    # commands based on vlan_matrix
    host_change_dict = change_cmd_gen(vlan_matrix)

    # call function ncsession to execute the change generated by change_cmd_gen
    report = ''
    for host,commands in host_change_dict.items():
        report = ncsession(host,uname,passwd,commands,mode,commit_at_time,confirm_time)
        print(report)

if __name__ == '__main__':
    main()
