import sys
import os
import random
import argparse
import datetime
from getpass import getpass
from jnpr.junos import Device
from jnpr.junos.exception import *
from jnpr.junos.utils.fs import *
from jnpr.junos.utils.scp import *
from jnpr.junos.utils.sw import *
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos.utils.config import Config
from utils import formatter, fireblade_hw
import concurrent.futures
from pprint import pprint

# get and process command line options
def getArgs():

    parser = argparse.ArgumentParser(description = 'General Queries & Configuration Changes Tool')
    
    # group arg_host 
    arg_host = parser.add_mutually_exclusive_group(required=True)
    arg_host.add_argument('-H', '--single_host', type=str, help='FQDN of a host')
    arg_host.add_argument('-l', '--hosts_list', metavar="FILE", help='Direcotry to a list of hosts')

    parser.add_argument('-x', '--action', type=str, required=True, default = 'rollback',  
        help='action after JUNOS is installed. Default to \'rollback\', other two options are ' + 
        '\'now\' for immediate rebooting or time string in format of \'yymmddhh\' to complete ' + 
        'the software installation. In last option fireblade.ji sets a random time offset ' + 
        '0-20 minutes for a host at the desired hour')
    parser.add_argument('-s', '--summary_log', metavar="FILE", required=True, help='Directory to an output file')

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

    return hosts, args.action, args.summary_log

# get credential
def getCredential():
    credential = ['','']
    uname = input('Username: ')
    credential[0] = uname.strip()
    passwd = getpass('Password: ')
    credential[1] = passwd
    return credential

# get and verify file
def getDir(args):
    while True:
        file_dir = input(f'Directory to JUNOS Package for {args}: ')
        if os.path.isfile(file_dir):
            return file_dir
        else:
            print ("Package Directory invalid, please try again")

# get junos installation package and md5 checksum
def getJUNOS():
    p_pkg = getDir('EX4300-48P')
    mp_pkg = getDir('EX4300-48MP')
    junos = {"p_pkg":p_pkg, "mp_pkg":mp_pkg}
    return junos

# logging installation
def myprogress(dev, report):
    now = datetime.datetime.now()
    with open(f'logs/{dev.hostname.split(".")[0]}-junosinstallation-{now.strftime("%Y")}-{now.strftime("%m")}-{now.strftime("%d")}.log', 'a') as fo:
        fo.write(f'{now.strftime("%H")}:{now.strftime("%M")} {report}\n')

# install junos on a chassis of same devices
def install_onepkg(dev, pkg, action):

    # test point
#    return True, dev.facts['hostname']

    sw = SW(dev)
    ok, msg = sw.install(package=pkg, validate=False, progress=myprogress)

    if ok:
        action_report = sw.reboot() if action == 'now' else sw.rollback() if action == 'rollback' else sw.reboot(at=action)

    return ok, msg, action_report

# install junos on a mixed chassis
def install_twopkg(dev, p_pkg, mp_pkg, action):

    # test point
#    return True, dev.facts['hostname']

    pkg_set = [p_pkg, mp_pkg]
    sw = SW(dev)
    ok, msg = sw.install(pkg_set=pkg_set, validate=False, progress=myprogress)

    if ok:
        action_report = sw.reboot() if action == 'now' else sw.rollback() if action == 'rollback' else sw.reboot(at=action)

    return ok, msg, action_report

# call installation fuctions for chassis
def installJUNOS(host, uname, passwd, junos, action):

    # set action o'{offset:02d}'r boot time
    if action not in ['rollback', 'now']:
        action += f'{random.randint(0, 20):02d}'

    try:
        with Device(host=host, user=uname, password=passwd) as dev:
            
            # chassis type dictates package
            chassis = fireblade_hw.chassis(dev)
            if chassis == 'EX4300-48P':
                pkg = junos["p_pkg"]
                ok, msg, action_report = install_onepkg(dev, pkg, action)
            elif chassis == 'EX4300-48MP':
                pkg = junos["mp_pkg"]
                ok, msg, action_report = install_onepkg(dev, pkg, action)
            elif chassis == 'mixed':
                p_pkg = junos["p_pkg"]
                mp_pkg = junos["mp_pkg"]
                ok, msg, action_report = install_twopkg(dev, p_pkg, mp_pkg, action)
            else:
                ok = False
                action_report = f'JUNOS installation on {host} is skipped due to hardware mismatch'

        return ok, host, action_report

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
        action = args[1]
        summary_log = args[2]

    except argparse.ArgumentError as err:
        print(f"Error: {err}")
        return

    # credential
    credential = getCredential()
    uname = credential[0]
    passwd = credential[1]

    # junos pkg info
    junos = getJUNOS()

    # run commands on each host in parallel

    print ('\nJUNOS installation is undergoing and may take hours. Please be patient.')
    print ('\nYou may track installation progress in below two ways:')
    print ('\n1) tail summary log file at ' + f'{summary_log} to view summary of the progress on targeted hosts, and')
    print ('2) tail log files named "host-junosinstallation-yyyy-mm-dd.log" for detailed progress on each host\n')

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(installJUNOS, host, uname, passwd, junos, action) for host in hosts]
        results =[]

        with open(summary_log,'a') as fo:

            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    now = datetime.datetime.now()
                    timestamp = f'{now.strftime("%Y")}-{now.strftime("%m")}-{now.strftime("%d")} {now.strftime("%H")}:{now.strftime("%M")}'
                    report = f"{timestamp} {result[1]}: JUNOS installation completed." if result[0] is True else f"{result[1]}: JUNOS installation failed."
                    report += '\n' + f"{timestamp} {result[1]} Post installation action: {result[2]}"
                    fo.write(report + '\n')
                    print ('\n'+report)
                    results.append(result)
                    results.append('\n')
                except Exception as err:
                    results.append(err)
                    results.append('\n')
    
            print ('results: ')
            print (results)

if __name__ == '__main__':
    main()
