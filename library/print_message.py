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
module: print_message
short_description: Prints a formatted message via the Ansible display mechanism
version_added: "2.9"
description:
    - Prints a message via the Ansible display mechanism using the colour and
      prefix associated with the chosen C(type).
    - If C(action) is provided, it is emitted as a separate C([ACTION]) line so
      that URLs are never broken mid-word by line-wrapping.
    - The module runs entirely on the controller — no remote connection needed.
options:
    msg:
        description:
            - The message to display.
        required: true
        type: str
    action:
        description:
            - Optional hint pointing to a follow-up action or documentation URL.
              Emitted on its own C([ACTION]) line to keep URLs intact and clickable.
            - Use the YAML literal block scalar C(|) so you control where newlines appear
              and can place URLs on their own line.
        required: false
        type: str
    type:
        description:
            - The message type which determines the colour and prefix used.
            - Supported types and their associated colours:
            - C(deprecate) — purple (C([DEPRECATED]))
            - C(info) — green (C([INFO]))
            - C(warning) — bright purple (C([WARNING]))
            - C(error) — red (C([ERROR]))
            - C(debug) — dark gray (C([DEBUG]))
            - C(verbose) — blue (C([VERBOSE]))
            - C(changed) — yellow (C([CHANGED]))
            - C(skip) — cyan (C([SKIP]))
            - C(unreachable) — bright red (C([UNREACHABLE]))
            - C(ok) — green (C([OK]))
            - C(included) — cyan (C([INCLUDED]))
        required: false
        type: str
        default: info
        choices:
            - deprecate
            - info
            - warning
            - error
            - debug
            - verbose
            - changed
            - skip
            - unreachable
            - ok
            - included
author:
    - metal-stack
notes:
    - Add C(run_once: true) to the task so Ansible only executes it once per play regardless of
      how many hosts are in the inventory. Without it the message appears once per host.
    - Output uses the colour associated with the chosen C(type) so it is visually distinct
      from generic C([WARNING]) messages.
'''

EXAMPLES = '''
# Deprecation message with an action pointing to a migration guide.
# Use | (literal block) for action so you control newlines and can place
# the URL on its own line, keeping it intact and clickable in log viewers.
# run_once: true ensures the message is only shown once per play even when
# the role is applied to multiple hosts:
- name: Deprecation warning
  run_once: true
  print_message:
    type: deprecate
    msg: >-
      The promtail role is deprecated and will be removed in a future release.
    action: |
      Use metal-roles/partition/roles/alloy instead - see README for instructions:
      https://github.com/metal-stack/metal-roles/tree/master/partition/roles/alloy#migration-from-promtail.

# Output:
# [DEPRECATED]: The promtail role is deprecated and will be removed in a future release.
# [ACTION]: Use metal-roles/partition/roles/alloy instead - see README for instructions:
# https://github.com/metal-stack/metal-roles/tree/master/partition/roles/alloy#migration-from-promtail.

# Info message without an action:
- name: Info message
  run_once: true
  print_message:
    type: info
    msg: Deployment completed successfully.

# Output:
# [INFO]: Deployment completed successfully.

# Warning message:
- name: Warning message
  run_once: true
  print_message:
    type: warning
    msg: This configuration is not recommended for production use.

# Output:
# [WARNING]: This configuration is not recommended for production use.
'''

RETURN = '''
msg:
    description: The message as passed to the module, without the display prefix.
    returned: always
    type: str
'''

def main():
    # Fallback error response if the action plugin fails to load.
    sys.stdout.write('{"failed": true, "msg": "The action plugin \'print_message\' was not loaded properly."}\n')
    sys.exit(0)

if __name__ == '__main__':
    main()
