#!/usr/bin/env python3

import subprocess
import re
import click
import random


def get_exit_node_list():
    """
    Retrieves the list of Tailscale exit nodes.
    """
    result = subprocess.run(
        ["tailscale", "exit-node", "list"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def parse_exit_nodes(output):
    """
    Parses the output of 'tailscale exit-node list'.
    """
    nodes = []
    for line in output.strip().split("\n"):
        if line.startswith("#"):
            continue
        # Split on 2 or more spaces
        parts = re.split(r'\s{2,}', line.strip())
        if len(parts) >= 4:
            nodes.append(
                {
                    "ip": parts[0],
                    "hostname": parts[1],
                    "country": parts[2],
                    "city": parts[3],
                }
            )
    return nodes


def get_unique_values(nodes, field):
    """
    Extracts a list of unique values for the given field.
    """
    return sorted(list({node[field] for node in nodes}))


def set_exit_node(ip_address):
    """
    Sets the Tailscale exit node.
    """
    subprocess.run(
        ["tailscale", "set", "--exit-node", ip_address],
        check=True,
        capture_output=True,
        text=True,
    )
    click.echo(f"Exit node set to: {ip_address}")


@click.command()
@click.argument('pattern')
@click.option('--by', '-b', type=click.Choice(['country', 'city', 'hostname']), 
              default='country', help='Field to match against')
@click.option('--dry-run', '-n', is_flag=True, help='Show selected node without activating it')
def main(pattern, by, dry_run):
    """
    A script to select a Tailscale exit node by matching pattern.
    
    PATTERN: Text to match against the chosen field (e.g. Sweden, London, us-nyc)
    """
    output = get_exit_node_list()
    nodes = parse_exit_nodes(output)
    values = get_unique_values(nodes, by)

    if not values:
        click.echo("No exit nodes found.", err=True)
        return

    # Find matching values based on substring
    matching_values = [v for v in values if pattern.lower() in v.lower()]
    
    if not matching_values:
        click.echo(f"Error: No {by} matching '{pattern}' found. Available {by}s: {', '.join(values)}", err=True)
        return
    
    if len(matching_values) > 1:
        click.echo(f"Error: Ambiguous match '{pattern}' matches multiple {by}s: {', '.join(matching_values)}", err=True)
        return
        
    matched_value = matching_values[0]
    filtered_nodes = [node for node in nodes if node[by] == matched_value]
    selected_node = random.choice(filtered_nodes)
    node_ip = selected_node["ip"]

    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", node_ip):
        click.echo("Invalid IP address format.", err=True)
        return

    if dry_run:
        click.echo(f"Would set exit node to: {node_ip} ({selected_node['hostname']}, {selected_node['city']}, {selected_node['country']})")
    else:
        set_exit_node(node_ip)


if __name__ == "__main__":
    main()
