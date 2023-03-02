import sys
import os
import datetime
from pathlib import Path
import argparse
from getpass import getpass
from jnpr.junos import Device
from jnpr.junos.exception import ConnectError
from jnpr.junos.utils.start_shell import StartShell
import formatter

def parse_arguments():
    parser = argparse.ArgumentParser(description='Example Argument Parser')
    arg_host = parser.add_mutually_exclusive_group(required=True)
    arg_host.add_argument('-l', '--hosts_list', metavar='FILE', help='List of hosts separated by commas')
    arg_host.add_argument('-H', '--single_host', type=str, help='Single host to process')
    parser.add_argument('-v', '--verbose', help='Verbose output with all inactive interfaces', action='store_true')
    args = parser.parse_args()

    if args.hosts_list and args.single_host:
        parser.error("Only one of --hosts_list or --single_host can be provided")

    return args

def main():
    try:
        args = parse_arguments()
        if args.hosts_list:
            with open(args.hosts_list) as f:
                hosts = [line.strip() for line in f.readlines() if not line.startswith('#')]
        else:
            hosts.append(args.single_host)

    except argparse.ArgumentError as e:
        print(f"Error: {e}")
        return

if __name__ == '__main__':
    main()