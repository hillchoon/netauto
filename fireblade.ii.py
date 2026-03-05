import sys
import os
import re
import datetime
import argparse
import hashlib
from lxml import etree
from getpass import getpass
from jnpr.junos import Device
from jnpr.junos.exception import *
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos.utils.config import Config
from jnpr.junos.utils.scp import SCP
from utils import formatter, fireblade_hw
import concurrent.futures

# get and process command line options
def getArgs():

    parser = argparse.ArgumentParser(description = 'Fireblade.ii for inventory of inactive interfaces on Juniper switches')

    # group arg_host
    arg_host = parser.add_mutually_exclusive_group(required=True)
    arg_host.add_argument('-H', '--hosts', nargs='+', 
        help='hosts\' FQDN in format of \'host1\' \'host2\'...single and double quote function the same.')
    arg_host.add_argument('-l', '--host_list', metavar="FILE", help='Direcotry of a list of hosts.')

    # agent slax file location
    parser.add_argument('-g', '--slax_file', metavar="FILE", required=True,
        help='Directory of a local slax agent file')

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

    return hosts, args.slax_file

# process credential
def getCredential():
    credential = ['','']
    uname = input('Username: ')
    credential[0] = uname.strip()
    passwd = getpass('Password: ')
    credential[1] = passwd
    return credential

# calculate MD5 hash of local file
def get_md5_hash(filepath):
    md5_hash = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

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
def action(host, uname, passwd, log_dir, slax_file, local_agent_hash):

    try:
        with Device(host=host, user=uname, password=passwd) as dev:

            # fetch hardware info
            hw_dict = fireblade_hw.hw_dict(dev)

            ## check if agent file exists on remote host
            # initialize varibles
            remote_path = '/var/db/scripts/op/portusage.slax'
            remote_agent_flag = False
            scp_agent_flag = True
            report = f'{host}\n'

            # Use PyEZ RPC to check if file exists
            remote_agent_report = dev.rpc.file_list(path=remote_path)

            # Check if remote agent exists by examining XML response
            # If agent doesn't exist: <output>path: No such file or directory</output>
            # If agent exists: <file-information><file-name>path</file-name></file-information>
            output_elm = remote_agent_report.find('.//output')
            file_info_elm = remote_agent_report.find('.//file-name')

            if output_elm is not None and 'No such file or directory' in output_elm.text:
                remote_agent_flag = False
            elif file_info_elm is not None:
                remote_agent_flag = True
            else:
                # unpected reponse format
                remote_agent_flag = False

            if remote_agent_flag:
                # remote agent exists, check its MD5 hash using RPC
                try:
                    remote_agent_md5_report = dev.rpc.get_checksum_information(path=remote_path)
                    # Extract MD5 from XML response: <checksum>hash</checksum>
                    checksum_elm = remote_agent_md5_report.find('.//checksum')

                    if checksum_elm is not None and checksum_elm.text:
                        remote_agent_hash = checksum_elm.text.strip()

                        if remote_agent_hash != local_agent_hash:
                            report += f'Local & remote agent MD5 hash mismatch, '
                            report += f'local agent is being copied to remote host\n'
                        else:
                            report += f'Remote agent verified'
                            scp_agent_flag = False
                    else:
                        report += f'Unable to extract remote MD5 hash, '
                        report += f'local agent is being copied to remote host\n'

                except Exception as checksum_err:
                    report += f'Error getting remote MD5 hash: {checksum_err}, '
                    report += f'local agent is being copied to remote host\n'

            else:
                # remote agent doesn't exist
                report += f'remtoe agent is not found, local agent is being copied to remote host\n'

            if scp_agent_flag:
                try:
                    with SCP(dev) as scp:
                        scp.put(slax_file, remote_path)

                    # initialize varibles
                    remote_agent_md5_report = None
                    checksum_elm = None
                    remote_agent_hash = None

                    # verify agent file integrity after scp
                    try:
                        remote_agent_md5_report = dev.rpc.get_checksum_information(path=remote_path)
                        checksum_elm = remote_agent_md5_report.find('.//checksum')

                        if checksum_elm is not None and checksum_elm.text:
                            remote_agent_hash = checksum_elm.text.strip()

                            if remote_agent_hash == local_agent_hash:
                                report += f'agent file copied and verified\n'
                            else:
                                raise Exception(f'MD5 checksum failed after scp')
                        else:
                            raise Exception('Unable to extract MD5 checksum from remote agent after scp')

                    except Exception as verify_err:
                        raise Exception(f'unable to verify MD5 checksum after scp: {verify_err}')

                except Exception as scp_err:
                    print(f'Error during SCP or verification: {scp_err}')
                    return None

            # getting bootdays
            up_times = [value['up_time'] for key, value in hw_dict.items() if isinstance(value, dict) and 'up_time' in value]
            max_sec = max(map(time_in_sec, up_times))
            weeks, remaining_seconds = divmod(max_sec, 7 * 24 * 60 * 60)
            days, remaining_seconds = divmod(remaining_seconds, 24 * 60 * 60)
            boot_wd = f'{days}d' if weeks == 0 else f'{weeks}w{days}d'

            # getting number of members
            n_member = sum(1 for key in hw_dict['model_info'].keys() if 'fpc' in key)

            # getting number of MP members
            n_mp = sum(1 for key, value in hw_dict['model_info'].items() if 'fpc' in key and value == 'EX4300-48MP')

            # getting number of P members
            n_p = sum(1 for key, value in hw_dict['model_info'].items() if 'fpc' in key and value == 'EX4300-48P')

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
                f_o.write(report)
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
        hosts, slax_file = getArgs()

    except argparse.ArgumentError as err:
        print(f"Error: {err}")
        return
    except FileNotFoundError as err:
        print(f"Error: {err}")
        return
    except Exception as err:
        print(f"Unexpected error parsing arguments: {err}")
        return

    # verify slax file exists and calculate MD5
    if not os.path.exists(slax_file):
        print(f"Error: SLAX file not found: {slax_file}")
        print(f"Please check the path and try again.")
        return

    if not os.path.isfile(slax_file):
        print(f"Error: Path exists but is not a file: {slax_file}")
        return

    # verify file is readable
    if not os.access(slax_file, os.R_OK):
        print(f"Error: SLAX file is not readable: {slax_file}")
        print(f"Please check file permissions and try again.")
        return

    # calculate MD5 hash
    try:
        local_md5 = get_md5_hash(slax_file)
        print(f"Local portusage.slax MD5: {local_md5}\n")
    except IOError as err:
        print(f"Error reading SLAX file: {err}")
        return
    except Exception as err:
        print(f"Error calculating MD5 hash: {err}")
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
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(action, host, uname, passwd, log_dir, slax_file, local_md5) for host in hosts]
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
