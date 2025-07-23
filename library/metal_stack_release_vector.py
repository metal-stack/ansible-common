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
module: metal_stack_release_vector
short_description: Downloads the metal-stack release vector OCI artifact
version_added: "2.15"
description:
    - This module downloads the metal-stack release vector OCI artifact, installs the included ansible-roles and
options:
    vectors:
        description:
            - The release version reference to download.
        required: false
    cache:
        description:
            - Whether or not to utilize a cache file for early returning on repeated module executions.
        required: false
author:
    - metal-stack
notes:
    - This module depends on the [opencontainers]("https://github.com/vsoch/oci-python") library.
'''

EXAMPLES = '''
- name: resolve metal-stack release vector
  metal_stack_release_vector:
    vectors:
      - url: oci://ghcr.io/metal-stack/releases:develop
        variable_mapping_path: metal_stack_release.mapping
        include_role_defaults: metal-roles/common/roles/defaults
  register: release_vector
'''
