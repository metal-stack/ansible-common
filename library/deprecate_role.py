#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys


ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: deprecate_role
short_description: Emits a deprecation warning for an Ansible role
version_added: "2.9"
description:
    - Emits a purple C([DEPRECATED]) message via the Ansible display mechanism to signal that a role is deprecated.
    - If C(alternative) is provided, it is emitted as a separate C([ALTERNATIVE]) line so that URLs
      are never broken mid-word by line-wrapping.
    - The module runs entirely on the controller — no remote connection needed.
options:
    msg:
        description:
            - The deprecation message to display.
        required: true
        type: str
    alternative:
        description:
            - Optional hint pointing to the replacement role or documentation URL.
              Emitted on its own C([ALTERNATIVE]) line to keep URLs intact and clickable.
            - Use the YAML literal block scalar C(|) so you control where newlines appear
              and can place URLs on their own line.
        required: false
        type: str
author:
    - metal-stack
notes:
    - Place a call to this module at the very top of a deprecated role's C(tasks/main.yaml).
    - Add C(run_once: true) to the task so Ansible only executes it once per play regardless of
      how many hosts are in the inventory. Without it the message appears once per host.
    - Output uses C(COLOR_DEPRECATE) (purple) so it is visually distinct from generic C([WARNING]) messages.
'''

EXAMPLES = '''
# With message and alternative pointing to a migration guide.
# Use | (literal block) for alternative so you control newlines and can place
# the URL on its own line, keeping it intact and clickable in log viewers.
# run_once: true ensures the message is only shown once per play even when
# the role is applied to multiple hosts:
- name: Deprecation warning
  run_once: true
  deprecate_role:
    msg: >-
      The promtail role is deprecated and will be removed in a future release.
    alternative: |
      Use metal-roles/partition/roles/alloy instead - see README for instructions:
      https://github.com/metal-stack/metal-roles/tree/master/partition/roles/alloy#migration-from-promtail.

# Output:
# [DEPRECATED]: The promtail role is deprecated and will be removed in a future release.
# [ALTERNATIVE]: Use metal-roles/partition/roles/alloy instead - see README for instructions:
# https://github.com/metal-stack/metal-roles/tree/master/partition/roles/alloy#migration-from-promtail.

# With only a message:
- name: Deprecation warning
  run_once: true
  deprecate_role:
    msg: This role is deprecated and will be removed in the next major release.

# Output:
# [DEPRECATED]: This role is deprecated and will be removed in the next major release.
'''

RETURN = '''
msg:
    description: The deprecation message as passed to the module, without the C([DEPRECATED]) display prefix.
    returned: always
    type: str
'''

def main():
    # Fallback error response if the action plugin fails to load.
    sys.stdout.write('{"failed": true, "msg": "The action plugin \'deprecate_role\' was not loaded properly."}\n')
    sys.exit(0)

if __name__ == '__main__':
    main()
