import sys
import os
import datetime
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

    parser = argparse.ArgumentParser(description = 'Fireblade.ii for inventory of inactive interfaces on Juniper switches')
    
    # group arg_host 
    arg_host = parser.add_mutually_exclusive_group(required=True)
    arg_host.add_argument('-H', '--hosts', nargs='+', 
        help='hosts\' FQDN in format of \'host1\' \'host2\'...single and double quote function the same.')
    arg_host.add_argument('-l', '--host_list', metavar="FILE", help='Direcotry to a list of hosts.')

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

    return hosts

# process credential
def getCredential():
    credential = ['','']
    uname = input('Username: ')
    credential[0] = uname.strip()
    passwd = getpass('Password: ')
    credential[1] = passwd
    return credential

# function time_in_sec
def time_in_sec(time):
    time_dict = {
        'weeks': 7 * 24 * 60 * 60,
        'days': 24 * 60 * 60,
        'hours': 60 * 60,
        'minutes': 60,
        'seconds': 1
    }
    seconds = 0
    for unit in time_dict.keys():
        match = re.search(r'(\d+)\s*{}'.format(unit), time)
        if match:
            seconds += int(match.group(1)) * time_dict[unit]
    return seconds

# netconf session for inactive interface inquiry
def action(host, uname, passwd, log_dir):

    try:
        with Device(host=host, user=uname, password=passwd) as dev:

            # fetch hardware info
            hw_dict = fireblade_hw.hw_dict(dev)

            # getting bootdays
            up_times = [value['up_time'] for key, value in hw_dict.items() if isinstance(value, dict) and 'up_time' in value]
            max_sec = max(map(time_in_sec, up_times))
            weeks, remaining_seconds = divmod(max_sec, 7 * 24 * 60 * 60)
            days, remaining_seconds = divmod(remaining_seconds, 24 * 60 * 60)
            boot_wd = f'{days}d' if weeks == 0 else f'{weeks}w{days}d'
            
            # getting number of members
            n_member = len(hw_dict['model_info'])

            # getting number of MP members
            n_mp = sum(value == 'EX4300-48MP' for value in hw_dict['model_info'].values())

            # getting number of P members
            n_p = sum(value == 'EX4300-48P' for value in hw_dict['model_info'].values())

            # getting number of total copper interfaces
            n_interface_total = 48 * n_member if n_mp != 0 or n_p != 0 else 12 * n_member

            host_shell = StartShell(dev)
            host_shell.open()

            # getting interfaces in status of 'down' and their last flap time
            cli_output = host_shell.run(f"cli -c 'op portusage | no-more'", timeout=600)[1]
            trimed_output = formatter.pop_first_last_lines(cli_output)
            
            # return error if error
            if re.match(r'.*error*', trimed_output[1]):
                result = f'{host} error message: {trimed_output[1]}'
                print (result)
                return result

            # extracting interfaces which last flap time is same as bootdays
            interface_pattern = r'\t(.*?)\t'
            time_pattern = r'\((.*?)\)'
            n_ii = 0
            list_ii = ''
            # match inactive interfaces
            for item in trimed_output:
                matching_time = re.search(time_pattern, item)
                interface = re.search(interface_pattern, item).group(1)
                matching_interface = interface if re.match(r'.*ge.*', interface) else None
                if matching_time and matching_interface and matching_time.group(1).split()[0] == boot_wd:
                    list_ii += f'{matching_interface}\n'
                    n_ii += 1

            # log list of inactive interfaces
            with open(f'{log_dir}/{host}.ii.list.log','a') as f_o:
                f_o.write(f'---inventory of inactive interfaces---\n{list_ii}')
                f_o.write(f'\n---portusage raw data---\n{trimed_output}')

            result = f'{host},{boot_wd},{n_member},{n_mp},{n_p},{n_interface_total},{n_ii},{round(100*n_ii/n_interface_total)}%'
            
            # log and screen ourput the report for this host 
            print (result)            
            return result

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
        hosts = getArgs()

    except argparse.ArgumentError as err:
        print(f"Error: {err}")
        return

    # credential
    credential = getCredential()
    uname = credential[0]
    passwd = credential[1]

    # create log directory if needed
    now = datetime.datetime.now()
    log_dir = f'./logs/inactive.interface.{now.strftime("%Y")}-{now.strftime("%m")}-{now.strftime("%d")}'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    print (f'\nFireblade.ii is inquiring the inventory of inactive interfaces on below chassis.\nAn summary for all chassis and their respective inventory files will be saved in directory:\n{log_dir}\n')
    print ('Hostname,Number of alive days,Number of members,Number of MPs,Number of Ps,Number of total interfaces,Number of inactive interfaces,Percentage of inactive interfaces')

    with open(f'{log_dir}/summary.log', 'w') as f_o:
        f_o.write('Hostname,Number of alive days,Number of members,Number of MPs,Number of Ps,Number of total interfaces,Number of inactive interfaces,Percentage of inactive interfaces\n')
        # run commands on each host in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(action, host, uname, passwd, log_dir) for host in hosts]
            concurrent.futures.wait(futures)

            for future in futures:
                try:
                    result = future.result()
                    if result:
                        f_o.write(f'{result}\n')

                except TypeError as err:
                    print (f'An error occurred: {err}')

if __name__ == '__main__':
    main()
