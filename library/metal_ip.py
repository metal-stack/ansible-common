#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.metal import AUTH_SPEC, exec_metalctl

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: metal_ip

short_description: A module to manage metal ip entities

version_added: "2.8"

description:
    - Manages ip entities in the metal-api.
    - Requires metalctl to be installed.
    - Cannot update entities.

options:
    name:
        description:
            - The description of the ip.
        required: false
    description:
        description:
            - The description of the ip.
        required: false
    ip:
        description:
            - The ip address to allocate.
        required: false
    network:
        description:
            - The network to allocate the ip in.
        required: false
    project:
        description:
            - The project of the ip.
        required: false
    type:
        description:
            - The type of the ip.
        default: static
        choices:
          - static
          - ephemeral
    state:
        description:
          - Assert the state of the ip.
          - >-
            Use C(present) to create or update a ip and C(absent) to
            delete it.
        default: present
        choices:
          - absent
          - present

author:
    - metal-stack
'''

EXAMPLES = '''
- name: allocate a specific ip
  metal_ip:
    ip: 212.34.83.13
    name: my-ip
    description: "my static ip"
    network: internet-fra-equ01
    type: static
    project: 9ec6882a-cd94-42a7-b667-ffaed43557c7

- name: allocate a random ip
  metal_ip:
    name: my-ip
    description: "my random ip"
    network: internet-fra-equ01
    type: static
    project: 9ec6882a-cd94-42a7-b667-ffaed43557c7

- name: free an ip
  metal_ip:
    ip: 212.34.83.13
    state: absent
'''

RETURN = '''
id:
  description:
    - ip address
  returned: always
  type: str
  sample: 212.34.83.13
'''


class Instance(object):
    def __init__(self, module):
        self._module = module
        self.changed = False
        self._ip = dict()
        self.ip_address = module.params.get('ip')
        self._name = module.params.get('name')
        self._project = module.params.get('project')
        self._network = module.params.get('network')
        self._description = module.params.get('description')
        self._type = module.params.get('type')
        self._state = module.params.get('state')

    def run(self):
        if self._module.check_mode:
            return

        self._find()

        if self._state == "present":
            if self._ip:
                return

            self._ip_allocate()
            self.changed = True

        elif self._state == "absent":
            if not self.ip_address:
                self._module.fail_json(msg="ip is a required argument when state is absent")
            if self._ip:
                self._ip_free()
                self.changed = True

    def _find(self):
        if not self.ip_address:
            return

        ips = self._ip_ls()

        for ip in ips:
            if ip["ipaddress"] == self.ip_address:
                self._ip = ip
                self.ip_address = ip["ipaddress"]

    def _ip_ls(self):
        args = ["network", "ip", "ls", "--ipaddress", self.ip_address]
        return exec_metalctl(self._module, args)

    def _ip_allocate(self):
        if not self._network:
            self._module.fail_json(msg="network is required when allocating an ip")
        if not self._project:
            self._module.fail_json(msg="project is required when allocating an ip")

        args = ["network", "ip", "allocate", "--project", self._project, "--network", self._network, "--type", self._type]

        if self._name:
            args += ["--name", self._name]
        if self._description:
            args += ["--description", self._description]
        if self.ip_address:
            args.append(self.ip_address)

        ip = exec_metalctl(self._module, args)

        if "ipaddress" not in ip:
            self._module.fail_json(msg="ip was not allocated properly", output=ip)

        self._ip = ip
        self.ip_address = ip["ipaddress"]

    def _ip_free(self):
        args = ["ip", "free", self.ip_address]
        ip = exec_metalctl(self._module, args)

        if "ipaddress" not in ip:
            self._module.fail_json(msg="ip was not freed properly", output=ip)


def main():
    argument_spec = AUTH_SPEC.copy()
    argument_spec.update(dict(
        ip=dict(type='str', required=False),
        name=dict(type='str', required=False),
        project=dict(type='str', required=False),
        description=dict(type='str', required=False),
        network=dict(type='str', required=False),
        type=dict(type='str', choices=['static', 'ephemeral'], default='static'),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
    ))
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    instance = Instance(module)

    instance.run()

    result = dict(
        changed=instance.changed,
        ip=instance.ip_address,
    )

    module.exit_json(**result)


if __name__ == '__main__':
    main()
