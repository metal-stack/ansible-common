#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: virtual_garden_kubeconfig
short_description: Retrieves a kubeconfig for accessing the virtual garden
version_added: "2.10"
description:
    - This relies on the virtual garden access kubeconfig being deployed through a managed resource as described in the Gardener docs.
    - Deploying a virtual garden like this can be achieved through the gardener operator.
    - On repeated execution the module only creates a new kubeconfig in case the kubeconfig token is about to expire.
options:
    kubeconfig:
        description:
            - The kubeconfig used for finding the garden resource.
            - Will be looked up from environment in case not defined.
    port:
        description:
            - The port that the virtual garden is exposed on. the default is 443.
            - If the port is not explicitly set the module will check if istio was exposed through an ingress resource, which is done for local setups (e.g. mini-lab). in this case it defaults to 4443.
        required: false
        default: 443
    garden_name:
        description:
            - The name of the garden resource to get the access kubeconfig for.
        required: false
        default: local
    token_secret_name:
        description:
            - The name the token secret for the virtual garden.
        required: false
        default: shoot-access-virtual-garden
    refresh_minutes:
        description:
            - On repeated execution creates a new kubeconfig if the token expiration is smaller than refresh_minutes.
        required: false
        default: 30
author:
    - metal-stack
notes:
    - Relies on the kubernetes python client library.
    - The refresh_minutes parameter does only have effect when pyjwt is installed.
'''

EXAMPLES = '''
- name: Retrieve virtual garden kubeconfig
  virtual_garden_kubeconfig:

# The expected module return will be:
# {"ansible_facts": {"gardener_virtual_garden_kubeconfig": "<a-kubeconfig>"}}
'''
