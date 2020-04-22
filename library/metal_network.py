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
module: metal_network

short_description: A module to manage metal network entities

version_added: "2.8"

description:
    - Manages network entities in the metal-api.
    - Requires metalctl to be installed.
    - Cannot update entities.

options:
    name:
        description:
            - >-
              The name of the network, which must be unique within a project and partition.
              Otherwise, the module cannot figure out if the network was already created or not.
        required: true
    description:
        description:
            - The description of the network.
        required: false
    partition:
        description:
            - The partition to allocate the network in.
        required: true
    project:
        description:
            - The project of the network.
        required: true
    state:
        description:
          - Assert the state of the network.
          - >-
            Use C(present) to create or update a network and C(absent) to
            delete it.
        default: present
        choices:
          - absent
          - present

author:
    - metal-stack
'''

EXAMPLES = '''
- name: allocate a network
  metal_network:
    name: my-network
    description: "my network"
    partition: fra-equ01
    project: 9ec6882a-cd94-42a7-b667-ffaed43557c7

- name: free a network
  metal_network:
    name: my-network
    project: 6df6a987-922d-4c36-8cd9-5edbd1584f7a
    partition: fra-equ01
    state: absent
'''

RETURN = '''
id:
    description:
        - network id
    returned: always
    type: str
    sample: 3e977e81-6ab5-4f28-b608-e7e94d62efb7
prefixes:
    description:
        - array of network prefixes
    returned: always
    type: list
    sample: ["10.0.112.0/22"]

'''


class Instance(object):
    def __init__(self, module):
        self._module = module
        self.changed = False
        self.prefixes = None
        self._network = dict()
        self.id = None
        self._name = module.params['name']
        self._project = module.params['project']
        self._partition = module.params['partition']
        self._description = module.params.get('description')
        self._state = module.params.get('state')

    def run(self):
        if self._module.check_mode:
            return

        self._find()

        if self._state == "present":
            if self._network:
                return

            self._network_allocate()
            self.changed = True

        elif self._state == "absent":
            if self._network:
                self._network_free()
                self.changed = True

    def _find(self):
        networks = self._network_ls()

        if len(networks) > 1:
            self._module.fail_json(
                msg="network name is not unique within a project and partition, which is required when "
                    "using this module",
                project=self._project, name=self._name)
        elif len(networks) == 1:
            self._network = networks[0]
            self.id = self._network["id"]
            self.prefixes = self._network["prefixes"]

    def _network_ls(self):
        args = ["network", "ls", "--name", self._name, "--partition", self._partition, "--project", self._project]
        return exec_metalctl(self._module, args)

    def _network_allocate(self):
        args = ["network", "allocate", "--name", self._name, "--description", self._description,
                "--project", self._project, "--partition", self._partition]
        network = exec_metalctl(self._module, args)

        if "id" not in network:
            self._module.fail_json(msg="network was not allocated properly", output=network)

        self._network = network
        self.id = self._network["id"]
        self.prefixes = self._network["prefixes"]

    def _network_free(self):
        args = ["network", "free", self.id]
        network = exec_metalctl(self._module, args)

        if "id" not in network:
            self._module.fail_json(msg="network was not freed properly", output=network)

        self._network = network
        self.id = network["id"]
        self.prefixes = self._network["prefixes"]


def main():
    argument_spec = AUTH_SPEC.copy()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        project=dict(type='str', required=True),
        description=dict(type='str', required=False),
        partition=dict(type='str', required=True),
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
        id=instance.id,
        prefixes=instance.prefixes,
    )

    module.exit_json(**result)


if __name__ == '__main__':
    main()
