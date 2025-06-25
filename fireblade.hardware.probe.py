import sys
import os
import argparse
from getpass import getpass
from jnpr.junos import Device
from jnpr.junos.exception import *
import concurrent.futures

def getCredential():
    credential = ['','']
    uname = input('Username: ')
    credential[0] = uname.strip()
    passwd = getpass('Password: ')
    credential[1] = passwd
    return credential

def getArgs():

    parser = argparse.ArgumentParser(description = 'General Hardware Information Inquiry Tool')

    # group arg_host 
    arg_host = parser.add_mutually_exclusive_group(required=True)
    arg_host.add_argument('-H', '--hosts', nargs='+', 
        help='hosts\' FQDN in format of \'host1\' \'host2\'...single and double quote function the same.')
    arg_host.add_argument('-l', '--host_list', metavar="FILE", help='Direcotry to a list of hosts.')

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

def probe(host, username, password):
    errmsg = 'No Error'
    hostname = model = model_info = ''

    try:
        with Device(host=host,user=username,password=password) as dev:
            hostname = dev.facts['hostname']
            model = dev.facts['model']
            model_info = dev.facts['model_info']

    except ConnectError as err:
        errmsg += f"Cannot connect to device: {err}"
    except ConnectAuthError as err:
        errmsg += f"Cannot authenticate to device: {err}"
    except ConnectTimeoutError as err:
        errmsg += f"Connection to device timed out: {err}"
    except ConnectRefusedError as err:
        errmsg += f"Connection to device was refused: {err}, please check NETCONF configuration"
    except RpcError as err:
        errmsg += f"RPC error: {err}"

    return hostname, model, model_info, errmsg

def main():
    
    try:
        hosts = getArgs()

    except argparse.ArgumentError as err:
        print(f"Error: {err}")
        return

    # credential
    credential = getCredential()
    uname = credential[0]
    passwd = credential[1]

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(probe, host, uname, passwd) for host in hosts]
        results = []

        for future in concurrent.futures.as_completed(futures):
            report = None
            try:
                result = future.result()
                #report = f"hostname: {result[0]}, model: {result[1]}, model_info: {result[2]}" if result[3] is '' else f"{result[3]}{host}"
                #print (report)
                results.append(result)
            except Exception as err:
                results.append(err)
        
        print (results)
            
if __name__ == '__main__':
    main()