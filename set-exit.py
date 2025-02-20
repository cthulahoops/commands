#!/usr/bin/env -S uv run
# dependencies = [
#     "click>=8.1.8",
#     "prompt-toolkit>=3.0.50",
#     "rich>=13.9.4",
# ]

import subprocess
import re
import click
import random


@click.command()
@click.argument("pattern")
@click.option(
    "--hostname", "-h", is_flag=True, help="Match against hostname instead of country"
)
@click.option(
    "--city", "-c", is_flag=True, help="Match against city instead of country"
)
@click.option(
    "--dry-run", "-n", is_flag=True, help="Show selected node without activating it"
)
def main(pattern, hostname, city, dry_run):
    """
    A script to select a Tailscale exit node by matching pattern.

    PATTERN: Text to match (e.g. Sweden, London, us-nyc)
    """

    if hostname:
        field = "hostname"
    elif city:
        field = "city"
    else:
        field = "country"

    selected_node = get_node(field, pattern)
    node_ip = selected_node["ip"]

    if dry_run:
        click.echo(
            f"Would set exit node to: {node_ip} ({selected_node['hostname']}, {selected_node['city']}, {selected_node['country']})"
        )
        return

    set_exit_node(node_ip)


def get_node(field, pattern):
    if pattern == "none":
        return {
            "ip": "",
            "hostname": "",
            "city": "",
            "country": "",
        }
    output = get_exit_node_list()
    nodes = parse_exit_nodes(output)

    values = get_unique_values(nodes, field)

    if not values:
        click.echo("No exit nodes found.", err=True)
        return

    matching_values = [v for v in values if pattern.lower() in v.lower()]

    if not matching_values:
        click.echo(
            f"Error: No {field} matching '{pattern}' found. Available {field}s: {', '.join(values)}",
            err=True,
        )
        return

    if len(matching_values) > 1:
        click.echo(
            f"Error: Ambiguous match '{pattern}' matches multiple {field}s: {', '.join(matching_values)}",
            err=True,
        )
        return

    matched_value = matching_values[0]
    filtered_nodes = [node for node in nodes if node[field] == matched_value]
    selected_node = random.choice(filtered_nodes)
    node_ip = selected_node["ip"]

    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", node_ip):
        click.echo("Invalid IP address format.", err=True)
        return

    return selected_node


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
        parts = re.split(r"\s{2,}", line.strip())
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


if __name__ == "__main__":
    main()
