# fireblade.nettop.py v1.0 - init
# takes lldp neighbors and service ip information from all network nodes
# maps network interconnections from core to remote node (top to bottom or left to right)

import argparse
import re
import sys

TARGET_KEYWORDS = [
    'edge',
    'ext',
    'pan',
    'ex4300',
    'csdc',
    'l1',
    'l2',
    'l3',
]
MAC_REGEX = re.compile(r'^[0-9a-f]{2}(:[0-9a-f]{2}){5}$', re.IGNORECASE)
IP_REGEX = re.compile(r'(\d{1,3}(?:\.\d{1,3}){3})/\d+')


def parse_lldp_log(filepath):
  with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

  sections = re.split(r'-{20,}', content)
  devices = {}

  for sec in sections:
    sec = sec.strip()
    if not sec:
      continue

    m_host = re.search(r'Host:\s*([^\s\n]+)', sec)
    if not m_host:
      continue

    host_name = m_host.group(1).strip().split('.')[0]
    in_cmd_output = False
    entries = []

    for line in sec.splitlines():
      line = line.strip()
      if not line:
        continue
      if line.startswith('Output for command:'):
        in_cmd_output = True
        continue
      if line.startswith('Cannot connect') or line.startswith('Host:'):
        continue
      if not in_cmd_output:
        continue

      parts = line.split()
      mac_idx = -1
      for idx, p in enumerate(parts):
        if MAC_REGEX.match(p):
          mac_idx = idx
          break

      if mac_idx == -1:
        continue

      local_intf = parts[0]
      parent_intf = parts[1] if mac_idx > 1 else '-'
      rem_parts = parts[mac_idx + 1 :]

      if len(rem_parts) >= 2:
        remote_intf = rem_parts[0]
        remote_sys = rem_parts[-1].split('.')[0]
      elif len(rem_parts) == 1:
        remote_intf = '-'
        remote_sys = rem_parts[0].split('.')[0]
      else:
        continue

      effective_intf = (
          parent_intf if parent_intf.startswith('ae') else local_intf
      )

      entries.append({
          'local_intf': local_intf,
          'parent_intf': parent_intf,
          'effective_intf': effective_intf,
          'remote_intf': remote_intf,
          'remote_sys': remote_sys,
      })

    devices[host_name] = entries

  return devices


def parse_service_ips(filepath):
  if not filepath:
    return {}

  with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

  sections = re.split(r'-{20,}', content)
  service_ips = {}

  for sec in sections:
    sec = sec.strip()
    if not sec:
      continue

    m_host = re.search(r'Host:\s*([^\s\n]+)', sec)
    if not m_host:
      continue

    host_name = m_host.group(1).strip().split('.')[0].lower()

    # Find ALL IPs in section to handle dual/multi-IP switches
    all_ips = IP_REGEX.findall(sec)
    if all_ips:
      service_ips[host_name] = [f'{ip}/32' for ip in all_ips]

  return service_ips


def is_target_neighbor(sys_name):
  return any(kw in sys_name.lower() for kw in TARGET_KEYWORDS)


def get_all_downstream_paths(current_switch, devices, visited=None):
  """Recursively discovers downstream switches down arbitrary daisy-chain depths."""
  if visited is None:
    visited = set()

  matching_key = next(
      (d for d in devices if d.lower() == current_switch.lower()), None
  )
  if not matching_key:
    return []

  visited.add(matching_key.lower())
  paths = []

  for sw_entry in devices[matching_key]:
    rem_sys = sw_entry['remote_sys']
    rem_sys_lower = rem_sys.lower()

    # Avoid loops, uplinks back to core, or unmonitored devices
    if (
        rem_sys_lower in visited
        or 'core' in rem_sys_lower
        or not is_target_neighbor(rem_sys)
    ):
      continue

    sw_intf = sw_entry['effective_intf']
    sub_paths = get_all_downstream_paths(rem_sys, devices, visited.copy())

    if sub_paths:
      for sp in sub_paths:
        paths.append([sw_intf, rem_sys] + sp)
    else:
      paths.append([sw_intf, rem_sys])

  return paths


def trace_connections(devices, service_ips):
  full_path_lines = []
  serviceip_map = []

  core_routers = [h for h in devices if 'core' in h.lower()]

  for core in sorted(core_routers):
    direct_switches = {}
    for entry in devices[core]:
      remote_sys = entry['remote_sys']
      if 'core' in remote_sys.lower() or not is_target_neighbor(remote_sys):
        continue
      if remote_sys not in direct_switches:
        direct_switches[remote_sys] = entry['effective_intf']

    for direct_switch, core_intf in sorted(direct_switches.items()):
      root_path = [core, core_intf, direct_switch]
      current_paths = [root_path]

      # Recursively collect all downstream chains
      downstream_chains = get_all_downstream_paths(
          direct_switch, devices, {core.lower()}
      )
      for chain in downstream_chains:
        current_paths.append(root_path + chain)

      # Append service IPs to furthest right switch
      for path in current_paths:
        furthest_switch = path[-1].strip().lower()
        matched_ips = service_ips.get(furthest_switch, [])

        if matched_ips:
          for ip in matched_ips:
            full_path_lines.append(','.join(path + [ip]))
            serviceip_map.append(f'{core},{core_intf},{ip}')
        else:
          full_path_lines.append(','.join(path))

  return full_path_lines, serviceip_map


def main():
  parser = argparse.ArgumentParser(
      description='Mapping Network Topology from Core to Remote Network.'
  )
  parser.add_argument(
      '-lldp', '--lldp', required=True, help='Path to LLDP log file'
  )
  parser.add_argument(
      '-ip',
      '--ip',
      default=None,
      help='Path to file listing switch service IPs',
  )

  args = parser.parse_args()

  devices = parse_lldp_log(args.lldp)
  service_ips = parse_service_ips(args.ip)
  full_paths, ip_map = trace_connections(devices, service_ips)

  # print output to screen
  print('=== FULL TOPOLOGY PATHS FROM ROUTER TO FURTHEST SWITCH ===')
  print('\n'.join(full_paths))

  if args.ip:
    print('\n=== SERVICE IP MAP ON ROUTER ===')
    print('\n'.join(ip_map))


if __name__ == '__main__':
  main()