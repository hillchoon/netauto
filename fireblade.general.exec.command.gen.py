#!/usr/bin/env python3
# fireblade.general.exec.command.gen.py v1.1 - added feature to skip comment lines in both template and variable definition files
# fireblade.general.exec.command.gen.py v1.0 - initial release

"""
fireblade.general.configuration.gen.py
A general configuration generator to populate Juniper configurations based on a template
(with {{ variable }} syntax) and a CSV file of variable values.
"""

import os
import sys
import re
import csv
import json
import argparse
import datetime

def parse_args():
    parser = argparse.ArgumentParser(
        description="General Execution Command Generator v1.1",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        '-t', '--template',
        required=True,
        metavar="FILE",
        help="Path to the execution command template (e.g., template.conf)"
    )
    
    parser.add_argument(
        '-d', '--data',
        required=True,
        metavar="FILE",
        help="Path to the CSV data file containing variable values"
    )
    
    parser.add_argument(
        '-o', '--output',
        required=True,
        metavar="PATH",
        help="Output path (destination file or directory)"
    )
    
    parser.add_argument(
        '-m', '--mode',
        choices=['c', 'i'],
        default='c',
        help="Output Mode: 'c' for consolidated (default), 'i' for individual"
    )
    
    parser.add_argument(
        '-f', '--format',
        choices=['i', 'j'],
        default='i',
        help="Output Format: 'i' for INI-alike (default), 'j' for JSON"
    )
    
    return parser.parse_args()

def get_hostname_column(headers):
    # Priority list for detecting hostname (case-insensitive check)
    priority_keys = ['fqdn', 'hostname', 'host', 'location', 'name']
    for pk in priority_keys:
        for header in headers:
            if header.strip().lower() == pk:
                return header
    # Fallback to the first column
    return headers[0]

def render_template(template_content, row_data):
    # Regex pattern to match {{ variable }} with optional whitespace
    pattern = r'\{\{\s*(\w+)\s*\}\}'
    
    def replacement_func(match):
        var_name = match.group(1)
        # Return the value from CSV or the placeholder if not found
        return str(row_data.get(var_name, match.group(0)))
        
    rendered = re.sub(pattern, replacement_func, template_content)
    
    # Split into lines, strip whitespace, filter out empty lines and comment lines starting with '#'
    commands = []
    for line in rendered.splitlines():
        cleaned = line.strip()
        if cleaned and not cleaned.startswith('#'):
            commands.append(cleaned)
    return commands

def main():
    args = parse_args()
    
    # 1. Verify existence of required input files
    if not os.path.isfile(args.template):
        print(f"Error: Template file not found: {args.template}", file=sys.stderr)
        sys.exit(1)
        
    if not os.path.isfile(args.data):
        print(f"Error: Data file not found: {args.data}", file=sys.stderr)
        sys.exit(1)

    # 2. Resolve target output path based on mode and folder checks
    mode = args.mode
    fmt = args.format
    output_path = args.output
    
    # Helper to check if a path represents a file (either an existing file or has an extension)
    def is_file_path(path):
        if os.path.exists(path):
            return os.path.isfile(path)
        _, ext = os.path.splitext(path)
        return ext != ''

    if mode == 'c':
        if os.path.isdir(output_path):
            print("Absence of a specific output file detected for consolidated mode.")
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            ext = "conf" if fmt == 'i' else "json"
            filename = f"general.configuration.{timestamp}.{ext}"
            resolved_output = os.path.join(output_path, filename)
            print(f"Generating consolidated config automatically in the output directory: {resolved_output}")
        else:
            resolved_output = output_path
            # Make sure parent directory exists
            parent_dir = os.path.dirname(resolved_output)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
    else:  # mode == 'i'
        if is_file_path(output_path):
            resolved_dir = os.path.dirname(output_path) or "."
            print(f"Output path is a specific file. Ignoring output file name and writing individual configurations into its directory: {resolved_dir}")
            resolved_output = resolved_dir
        else:
            resolved_output = output_path
            
        if not os.path.exists(resolved_output):
            os.makedirs(resolved_output, exist_ok=True)

    # 3. Read template
    with open(args.template, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Extract all variables defined in the template
    template_vars = set(re.findall(r'\{\{\s*(\w+)\s*\}\}', template_content))

    # 4. Read CSV data
    host_configs = {}
    
    with open(args.data, 'r', newline='', encoding='utf-8') as f:
        # Filter out lines that start with '#' (ignoring leading whitespace)
        non_comment_lines = [line for line in f if not line.lstrip().startswith('#')]

    if not non_comment_lines:
        print("Error: The CSV data file is empty after filtering comments.", file=sys.stderr)
        sys.exit(1)

    # Parse headers from the first non-comment line
    reader = csv.DictReader(non_comment_lines)
    if not reader.fieldnames:
        print("Error: The CSV data file has no headers.", file=sys.stderr)
        sys.exit(1)
        
    headers = [h.strip() for h in reader.fieldnames]
    
    # Recreate DictReader with the non-comment lines (skipping the header line)
    reader = csv.DictReader(non_comment_lines[1:], fieldnames=headers)
    
    # Determine the column for hostname
    hostname_col = get_hostname_column(headers)
    print(f"Auto-resolved hostname column: '{hostname_col}'")
    
    # Validate that all template variables exist in the CSV headers
    missing_vars = [v for v in template_vars if v not in headers]
    if missing_vars:
        print(f"Error: The following variables in the template are missing from the CSV headers: {missing_vars}", file=sys.stderr)
        sys.exit(1)
        
    for row_idx, row in enumerate(reader, start=2):
        # Strip whitespace from keys and values
        cleaned_row = {k.strip(): v.strip() for k, v in row.items() if k is not None and v is not None}
        
        # Retrieve hostname
        hostname = cleaned_row.get(hostname_col)
        if not hostname:
            print(f"Warning: Row {row_idx} is missing a value for hostname column '{hostname_col}'. Skipping row.")
            continue
            
        # Render template for this host
        commands = render_template(template_content, cleaned_row)
        host_configs[hostname] = commands

    # 5. Write configurations
    if mode == 'c':
        if fmt == 'i':
            # Consolidated INI format
            output_content = ""
            for host, commands in host_configs.items():
                output_content += f"[{host}]\n"
                for cmd in commands:
                    output_content += f"{cmd}\n"
                output_content += "\n"
            with open(resolved_output, 'w', encoding='utf-8') as f:
                f.write(output_content)
        else:
            # Consolidated JSON format
            with open(resolved_output, 'w', encoding='utf-8') as f:
                json.dump(host_configs, f, indent=2)
        print(f"Consolidated configuration successfully written to: {resolved_output}")
    else:
        # Individual mode
        for host, commands in host_configs.items():
            if fmt == 'i':
                filename = f"{host}.conf"
                file_path = os.path.join(resolved_output, filename)
                output_content = f"[{host}]\n" + "\n".join(commands) + "\n"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(output_content)
            else:
                filename = f"{host}.json"
                file_path = os.path.join(resolved_output, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({host: commands}, f, indent=2)
        print(f"Individual configuration files successfully written to directory: {resolved_output}")

if __name__ == '__main__':
    main()
