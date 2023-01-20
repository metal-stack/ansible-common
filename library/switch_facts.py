#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os.path
from ansible.module_utils.basic import AnsibleModule


ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: switch_facts
short_description: Finds out facts about metal-stack switches.
version_added: "2.9"
description:
    - Can be used just as gather_facts.
author:
    - metal-stack
'''

EXAMPLES = '''
# Let's you gather switch facts
- name: gather switch facts
  switch_facts:
'''


def file_contains(path, s):
    try:
      with open(path, 'r') as f:
          if s.lower() in f.read().lower():
              return True
    except:
      return False
    return False


if __name__ == '__main__':
    module_args = dict()

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    switch_os = "unknown"
    is_sonic = False
    is_cumulus = False

    if os.path.isfile("/etc/sonic/sonic_version.yml"):
        switch_os = "sonic"
        is_sonic = True
    elif file_contains("/etc/os-release", "Cumulus Linux"):
        switch_os = "cumulus"
        is_cumulus = True

    result = dict(
        ansible_facts=dict(
            metal_stack_switch_os_name=switch_os,
            metal_stack_switch_os_is_sonic=is_sonic,
            metal_stack_switch_os_is_cumulus=is_cumulus,
        )
    )

    module.exit_json(**result)
