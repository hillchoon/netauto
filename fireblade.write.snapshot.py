# fireblade.write.snapshot v1.0
# features:
# 1. 50 sessions in parallel
# 2. write snapshot to alternative partition on ex4300p non-mixed chassis
# 3. write snapshot to P members one by one on ex4300mp mixed chassis
# 4. write report from each host to a dedicated log file

import os
import re
import sys
import argparse
from getpass import getpass
from jnpr.junos import Device
from jnpr.junos.exception import *
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos.utils.config import Config
from utils import formatter, fireblade_hw
import concurrent.futures
import datetime

# get and process command line options
def getArgs():

    parser = argparse.ArgumentParser(
        description = 'EX4300P switches snapshot writer',
        formatter_class=argparse.RawTextHelpFormatter
        )

    # group arg_host
    arg_host = parser.add_mutually_exclusive_group(required=True)
    arg_host.add_argument('-H', '--hosts', nargs='+', 
        help='hosts\' FQDN in format of \'host1\' \'host2\'...single and double quote function the same.')
    arg_host.add_argument('-l', '--host_list', metavar="FILE", help='Direcotry to a list of hosts.')

    # arg 'runtime_log'
    parser.add_argument('-g', '--runtime_log', metavar="FILE", required=True, help='Directory to a runtime log for reports from all hosts')

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

    return hosts, args.runtime_log

# process credential
def getCredential():
    credential = ['','']
    uname = input('Username: ')
    credential[0] = uname.strip()
    passwd = getpass('Password: ')
    credential[1] = passwd
    return credential

# ANSI escape codes for colors
class bcolors:
    OKGREEN = '\033[92m'
    OKBLUE = '\033[94m'
    ENDC = '\033[0m'

# get timestamp
def clock():
    now = datetime.datetime.now()
    timestamp = f'{now.strftime("%Y")}-{now.strftime("%m")}-{now.strftime("%d")} {now.strftime("%H")}:{now.strftime("%M")}'
    return timestamp

# process write - write snapshot to alternative slice on certain members
def WriteSnapshot(dev,member):

    # initial report
    report = ''

    # write snapshot to P members in mixed chassis
    if member == 'mixed':
         with StartShell(dev) as dev_sh:
            # get all P members in the chassis
            pmembers = formatter.pop_first_last_lines(
                dev_sh.run('cli -c "show virtual-chassis | match ex4300-48p | no-more"')[1]
                )
            report += f'\n{bcolors.OKGREEN}----This is a mixed chassis with below {len(pmembers)} FPCs of EX4300-48P---------------{bcolors.ENDC}\n\n'
            report += '\n'.join(pmembers) + '\n'

            # create a list of P fpcs
            fpc = []
            for line in pmembers:
                match = re.search(r'\(FPC (\d+)\)', line)
                if match:
                    fpc.append(match.group(1))

            # write snapshot on each pmember in list fpc
            for pmember in fpc:
                report += f'\n{bcolors.OKGREEN}----Writing snapshot on fpc{pmember}----------------------------------------------{bcolors.ENDC}\n'
                report += '\n'.join(
                    formatter.pop_first_last_lines(
                        dev_sh.run('rlogin -Ji fpc'+f'{pmember}')[1]
                        )
                    )
                report += '\n'.join(
                    formatter.pop_first_last_lines(
                        dev_sh.run('request system snapshot local slice alternate',timeout=120)[1]
                        )
                    )
                report += f'\n\n{bcolors.OKGREEN}----Partitions on fpc{pmember} after snapshot is written--------------------------{bcolors.ENDC}\n\n'
                report += '\n'.join(
                    formatter.pop_first_last_lines(
                        dev_sh.run('show system snapshot local media internal')[1]
                        )
                    )
                report += '\n'.join(
                    formatter.pop_first_last_lines(dev_sh.run('exit')[1])
                    )
                report += f'\n{bcolors.OKGREEN}----Writing snapshot on fpc{pmember} is completed---------------------------------{bcolors.ENDC}'
    # write snapshot to all members on a P chassis
    else:
        dev.timeout = 1200
        with StartShell(dev) as dev_sh:
            pmembers = formatter.pop_first_last_lines(
                    dev_sh.run('cli -c "show virtual-chassis | match FPC | no-more"')[1]
                    )
        report += f'\n{bcolors.OKGREEN}----This is an EX4300-48P non-mixed chassis with {len(pmembers)} FPCs below-------------{bcolors.ENDC}\n\n'
        report += '\n'.join(pmembers)
        report += f'\n\n{bcolors.OKGREEN}----Writing snapshot in fpc order-----------------------------------------{bcolors.ENDC}'
        report += f"\n{dev.cli('request system snapshot all-members slice alternate',warning=False)}"
        report += f'\n{bcolors.OKGREEN}----Writing Snapshot on entire chassis is completed, see partitions-------{bcolors.ENDC}\n\n'
        with StartShell(dev) as dev_sh:
            report += '\n'.join(
                formatter.pop_first_last_lines(
                    dev_sh.run('cli -c "show system snapshot all-members media internal | no-more"',timeout=180)[1]
                    )
                )
    return report

# process drive - drive the writing of snapshot if the chassis is a MP mixed or P non-mixed chassis
def drive(host,uname,passwd):

    # initial report
    report = f"{bcolors.OKBLUE}----------------------------------------------------------------------------------------{bcolors.ENDC}\nHost: {host}\n"
    report += f'Start: {clock()}\n'

    try:
        with Device(host=host, user=uname, password=passwd) as dev:
            chassis = fireblade_hw.chassis(dev)
            if chassis == 'EX4300-48P':
                report += WriteSnapshot(dev,'all-member')
            elif chassis == 'mixed':
                report += WriteSnapshot(dev,'mixed')
            else:
                report += f'{host} does not contain any ex4300-48p members, skipped'

        return f'{report}\n\nEnd: {clock()}\n'

    except ConnectError as err:
        print(f"{clock()} Cannot connect to device: {err}")
    except ConnectAuthError as err:
        print(f"{clock()} Cannot authenticate to device: {err}")
    except ConnectTimeoutError as err:
        print(f"{clock()} Connection to device timed out: {err}")
    except ConnectRefusedError as err:
        print(f"{clock()} Connection to device was refused: {err}, please check NETCONF configuration")
    except RpcError as err:
        print(f"{clock()} RPC error: {err}")

def main():

    # command line arguments
    try:
        args = getArgs()
        hosts = args[0]
        runtime_log = args[1]

    except argparse.ArgumentError as err:
        print(f"Error: {err}")
        return

    # credential
    credential = getCredential()
    uname = credential[0]
    passwd = credential[1]

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(drive, host, uname, passwd) for host in hosts]
        results =''

        with open(runtime_log,'a') as fo:
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    fo.write(result + '\n')
                    results += f'{result}\n'
                except Exception as err:
                    print(err)
                    fo.write(f'{err}\n')
                    results += f'{err}\n'

            print (f'(Writing Snapshot on Hosts:\n{results}')

if __name__ == '__main__':
    main()

