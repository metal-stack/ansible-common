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
version_added: "2.18"
description:
    - This module downloads a metal-stack release vector OCI artifact.
    - It can be used to install included ansible-roles and map values in the release vector to ansible variables (usually making release component versions available as Ansible variables).
    - The module can also install from Git Repositories as an alternative to OCI artifacts.
    - It is possible to validate the authenticity of an OCI artifact using cosign.
options:
    vectors:
        description:
            - The release vector reference to download.
            - This option can also be set through the metal_stack_release_vectors variable from somewhere in the task vars.
        type: list
        elements: dict
        required: false
        suboptions:
            url:
                description:
                    - The URL where the release vector artifact resides.
                    - If the URL starts with the prefix "oci://", the release vector is downloaded as an OCI artifact.
                    - If not starting with oci:// prefix, the module downloads the URL using ansible.module_utils.urls.
                required: true
                type: str
            variable_mapping_path:
                description:
                    - A dotted path to a variable (somewhere in the task vars) containing a mapping from variable names to paths in the release vector.
                    - The mapping key is the variable name used to be returned as an ansible fact by the module.
                    - The mapping value is a dotted path to a value in the release vector.
                    - In case a variable in the mapping is already defined in the task vars, the module does not overwrite it, such that variables can be easily overwritten.
                    - Usually these mapping are provided by a metal-stack ansible-role and can be included for lookup using the include_role_defaults option.
                required: false
                type: str
            include_role_defaults:
                description:
                    - If the variable mapping does not exist in the task vars, with this option it is also possible to include role defaults into the lookup.
                    - When using this in combination with the install_roles option, it is also possible to include role defaults from ansible-roles defined in the release vector.
                    - This way, roles from the release vector can ship a variable mapping, too.
                required: false
                type: str
            nested:
                description:
                    - A list of nested release vectors that may reside in the downloaded release vector.
                    - The elements of this option contain the same options as the vectors option with the single difference of having a "url_path" instead of an "url" option.
                    - The "url_path" is a dotted path to a value in the release vector.
                    - Variable mappings of nested releases do not overwrite variables from the parent release vector mapping.
                required: false
                type: list
                elements: dict
            install_roles:
                description:
                    - If set to true, installs ansible roles from the downloaded release vector.
                    - By default it installs the roles from an "ansible-roles" dictionary defined on the root of the release vector.
                    - Alternatively, the path to the ansible roles dictionary can be overwritten using the ansible_roles_path option.
                    - This option can also be set through the metal_stack_release_vector_install_roles variable from somewhere in the task vars.
                required: false
                default: true
                type: bool
            ansible_roles_path:
                description:
                    - A dotted path to the "ansible-roles" dictionary in the release vector when using the install_roles option.
                    - By default the module uses the "ansible-roles", this is option is just a possible overwrite for this option.
                required: false
                type: str
            role_aliases:
                description:
                    - An optional list of aliases to modify the installation path for the ansible-role installation.
                type: list
                elements: dict
                suboptions:
                    repository:
                        description:
                            - The name of the role repository to alias.
                        required: true
                        type: str
                    alias:
                        description:
                            - The alias for the role.
                        required: true
                        type: str
            replace:
                description:
                    - Allows partial replacements of variable values that are returned as facts by this module.
                    - This allows for instance rewriting a registries different from the one's defined in the release vector.
                    - This option can also be set through the metal_stack_release_vector_replacements variable from somewhere in the task vars.
                required: false
                type: list
                elements: dict
                suboptions:
                    key:
                        description:
                            - The key to replace.
                        required: true
                        type: str
                    old:
                        description:
                            - A partial string to replace.
                        required: true
                        type: str
                    new:
                        description:
                            - The value to replace the value specified by the old option with.
                        required: true
                        type: str
            oci_registry_username:
                description:
                    - The username to authenticate against the OCI registry.
                required: false
                type: str
            oci_registry_password:
                description:
                description:
                    - The password to authenticate against the OCI registry.
                required: false
                type: str
            oci_registry_scheme:
                description:
                    - The scheme to communicate with the OCI registry.
                required: false
                type: str
                default: https
            oci_cosign_verify_certificate_identity:
                description:
                    - The certificate identity used for validating the OCI artifact with cosign.
                    - This is used for artifacts that are signed keyless.
                required: false
                type: str
            oci_cosign_verify_certificate_oidc_issuer:
                description:
                    - The OIDC issuer used for validating the OCI artifact with cosign.
                    - This is used for artifacts that are signed keyless.
                required: false
                type: str
            oci_cosign_verify_key:
                description:
                    - The public key used for validating the OCI artifact with cosign.
                required: false
                type: str
    cache:
        description:
            - Whether or not to utilize a cache file for early returning on repeated module executions.
        type: bool
        required: false
author:
    - metal-stack
notes:
    - OCI artifacts downloaded by this module are expected to be shipped as a metal-stack release vector OCI artifact including a layer typed "application/vnd.metal-stack.release-vector.v1.tar+gzip".
    - Ansible roles that can be defined in the release vector as OCI artifacts and installed by this module are expected to be metal-stack ansible-role OCI artifacts including a layer typed "application/vnd.metal-stack.ansible-role.v1.tar+gzip".
    - This module depends on the [opencontainers]("https://github.com/vsoch/oci-python") library.
    - If cosign validation is desired, the module depends on cosign to be installed on the host system.
'''

EXAMPLES = '''
- name: resolve metal-stack release vector
  metal_stack_release_vector:
    vectors:
      - url: oci://ghcr.io/metal-stack/releases:develop
        variable_mapping_path: metal_stack_release.mapping
        include_role_defaults: metal-roles/common/roles/defaults
  register: release_vector

# see integration.yaml in test folder for more examples
'''
