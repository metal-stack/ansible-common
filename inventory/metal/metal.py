#!/usr/bin/env python

import argparse
import os
import json
import subprocess
import yaml

METALCTL_BIN = os.environ.get("METALCTL_BIN", "metalctl")

CONFIG_PATH = os.environ.get("METAL_ANSIBLE_INVENTORY_CONFIG",
                             os.path.join(os.path.dirname(__file__), "metal_config.yaml"))
CONFIG = dict()
if os.path.isfile(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as f:
        CONFIG = yaml.safe_load(f)


def run():
    args = parse_arguments()
    if args.host:
        result = host_vars(args.host)
    else:
        result = host_list()

    return_json(result)


def parse_arguments():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--list",
        action="store_true",
        help="lists groups and hosts"
    )
    group.add_argument(
        "--host",
        help="returns host variables of the dynamic inventory source"
    )
    return parser.parse_args()


def host_list():
    cmd = [METALCTL_BIN, "machine", "ls", "-o", "json"]
    env = os.environ.copy()

    metalctl_url = CONFIG.get("metalctl_url", "")
    if metalctl_url:
        cmd.append("--url=%s" % metalctl_url)

    metalctl_hmac = CONFIG.get("metalctl_hmac", "")
    if metalctl_hmac:
        env["METALCTL_HMAC"] = metalctl_hmac

    scope_filters = CONFIG.get("scope_filters", [])
    for scope_filter in scope_filters:
        cmd.append("--%s=%s" % (scope_filter["name"], scope_filter.get("value", "")))

    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, env=env)
    except subprocess.CalledProcessError as e:
        raise Exception("listing machines failed with return code %d: %s" % (e.returncode, e.output))

    machines = json.loads(out.decode())

    machine_meta = dict()
    inventory = {"_meta": dict(hostvars=machine_meta)}

    static_machine_ip_mapping = CONFIG.get("static_machine_ip_mapping", dict())

    for machine in machines:
        id = machine.get("id")
        description = machine.get("description")
        rack_id = machine.get("rackid")
        allocation = machine.get("allocation")
        size_id = machine.get("size").get("id") if machine.get("size") else None
        partition_id = machine.get("partition").get("id") if machine.get("partition") else None
        tags = machine.get("tags", [])

        if not allocation or not id:
            continue

        networks = allocation.get("networks", {})
        console_password = allocation.get("console_password")
        name = allocation.get("name", "")
        hostname = allocation.get("hostname", "")
        project_id = allocation.get("project")
        tenant_id = allocation.get("tenant")
        image = allocation.get("image")
        image_id = None
        if image:
            image_id = image.get("id")

        primary_ip = None
        for network in networks:
            is_primary = network.get("primary")
            if is_primary:
                primary_ips = network.get("ips")
                if len(primary_ips) > 0:
                    primary_ip = primary_ips[0]
                    break

        # TODO: It is somehow hard to determine the IP of the machine to connect with from the internet...
        external_ip = None
        for network in networks:
            is_external = True if "internet" in network.get("networkid", "") else False
            if is_external:
                external_ips = network.get("ips")
                if len(external_ips) > 0:
                    external_ip = external_ips[0]
                    break

        ansible_host = allocation.get("hostname", name)
        ansible_host = external_ip if external_ip is not None else ansible_host
        if not ansible_host:
            # if there is no name, no host name and no external ip... we skip this host
            continue

        is_machine = False
        is_firewall = False

        if image:
            image_features = image.get("features", [])

            if "firewall" in image_features:
                if len(networks) > 1:
                    is_firewall = True
            if "machine" in image_features:
                is_machine = True

        machine_meta[hostname] = dict(
            ansible_host=ansible_host,
            metal_id=id,
            metal_name=name,
            metal_hostname=hostname,
            metal_description=description,
            metal_rack_id=rack_id,
            metal_project_id=project_id,
            metal_console_password=console_password,
            metal_tenant_id=tenant_id,
            metal_is_firewall=is_firewall,
            metal_is_machine=is_machine,
            metal_tags=tags,
        )

        _append_to_inventory(inventory, project_id, hostname)
        _append_to_inventory(inventory, size_id, hostname)
        _append_to_inventory(inventory, partition_id, hostname)
        _append_to_inventory(inventory, image_id, hostname)
        _append_to_inventory(inventory, "metal", hostname)

        if primary_ip:
            machine_meta[hostname]["metal_internal_ip"] = primary_ip
        if size_id:
            machine_meta[hostname]["metal_size_id"] = size_id
        if partition_id:
            machine_meta[hostname]["metal_partition_id"] = partition_id
        if image_id:
            machine_meta[hostname]["metal_image_id"] = image_id

        if hostname in static_machine_ip_mapping:
            machine_meta[hostname]["ansible_host"] = static_machine_ip_mapping[hostname]

    return inventory


def _append_to_inventory(inventory, key, host):
    if not key:
        return

    if key not in inventory:
        inventory[key] = []

    hosts = inventory[key]
    hosts.append(host)


def host_vars(host):
    # currently not required because host list returns _meta information
    return dict()


def return_json(result):
    print(json.dumps(result, sort_keys=True, indent=4))


if __name__ == '__main__':
    run()
