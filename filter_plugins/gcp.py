from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

from ansible.errors import AnsibleFilterError


def extract_gcp_node_network(subnets, region):
    for subnet in subnets:
        subnetwork = subnet.get("subnetwork")
        if not subnetwork:
            continue

        if region in subnetwork:
            return subnet.get("ipCidrRange")

    raise AnsibleFilterError("no node network found for region: %s" % region)


class FilterModule(object):
    def filters(self):
        return {
            'extract_gcp_node_network': extract_gcp_node_network,
        }
