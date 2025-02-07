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


def get_unique_countries(nodes):
    """
    Extracts a list of unique countries.
    """
    return sorted(list({node["country"] for node in nodes}))


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
@click.argument('country')
@click.option('--dry-run', '-n', is_flag=True, help='Show selected node without activating it')
def main(country, dry_run):
    """
    A script to select a Tailscale exit node by country.
    
    COUNTRY: Name of the country to use (e.g. Sweden)
    """
    output = get_exit_node_list()
    nodes = parse_exit_nodes(output)
    countries = get_unique_countries(nodes)

    if not countries:
        click.echo("No exit nodes found.", err=True)
        return

    # Find matching countries based on substring
    matching_countries = [c for c in countries if country.lower() in c.lower()]
    
    if not matching_countries:
        click.echo(f"Error: No country matching '{country}' found. Available countries: {', '.join(countries)}", err=True)
        return
    
    if len(matching_countries) > 1:
        click.echo(f"Error: Ambiguous match '{country}' matches multiple countries: {', '.join(matching_countries)}", err=True)
        return
        
    matched_country = matching_countries[0]
    filtered_nodes = [node for node in nodes if node["country"] == matched_country]
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
