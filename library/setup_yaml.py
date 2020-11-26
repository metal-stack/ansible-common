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
module: setup_yaml
short_description: Resolves variables from a remote YAML file
version_added: "2.9"
description:
    - This module maps contents of a remote YAML file to ansible_facts according to a given variable mapping. 
    - Within a YAML file, it is also possible to point to other YAML files, which will then be resolved recursively.
    - This module can pick up some variables "magically", which makes the module very versatile
      but also causes some conventions that need to be followed when using this module. 
    - Please check out the examples of how to use it.
options:
    files:
        description:
            - A list of files to be resolved.
            - The module will not fail but skip if this variable is not provided.
            - This parameter can be "magically" provided by defining the variable `setup_yaml`
        required: false
    smart:
        description:
            - Will make this module skip in case it was already executed. 
              Sets a marker into the vars to prevent repeated execution.
            - This parameter can be "magically" provided by defining the variable `setup_yaml_smart`
        required: false
        default: true
    recursive:
        description:
            - Can be used to disable recursive resolution of other files. This can be useful in certain situations.
        required: false
        default: true
    replace:
        description:
            - A list of replacements that can be used for recursively replacing string values for given keys in
              the remote file content.
        required: false
author:
    - metal-stack
notes:
    - We typically use this module for dynamically providing docker image version variables to ansible roles. 
      In the metal-stack docs, we will also call the contents of the downloaded YAML file a release vector.
'''

EXAMPLES = '''
# Assume a YAML file containing release versions of docker-images at https://example.com/v1.0.0/example.yaml, which
# looks like this:
#
# ---
# docker-images:
#   hello-world:
#     name: hello-world
#     tag: v0.2.0
# ...
# 
# Let's now define the following task:

- name: gather release versions
  setup_yaml:
    files:
      - url: https://example.com/v1.0.0/example.yaml
        mapping:
          hello_world_image_tag: "docker-images.hello-world.tag"

# The expected module return will be:
# {"ansible_facts": {"hello_world_image_tag": "v0.2.0"}}
#
# Remember that ansible_facts are automatically added to the host vars by ansible, such that they are immediately
# available for further usage.
#
#
# It would also be possible to pickup the module parameters "magically". Let's create the following variables somewhere
# in your playbook:
#
# ---
# setup_yaml:
#   - url: https://example.com/v1.0.0/example.yaml
#     meta_var: example_release
#
# example_release:
#  mapping:
#    hello_world_image_tag: "docker-images.hello-world.tag"
# ...
#
# Then, you could just write a task definition like this:

- name: gather release versions
  setup_yaml:

# The "magic" lookup is extremely helpful because the "example_release" variable can be provided by external roles.
# This could mean that the direct consumer does not need to know the variable mapping.
#
# It is also possible to nest yaml files into each other, making a recursive resolution:
#
#
- name: gather release versions
  setup_yaml:
    files:
      - url: https://example.com/v1.0.0/example.yaml
        mapping:
          hello_world_image_tag: "docker-images.hello-world.tag"
        nested:
          - url_path: "other-files.example-2.url"
            mapping:
              hello_world_2_image_tag: "docker-images.hello-world-2.tag"
#
# Recursive resolution can also use the "magic" lookup!
#
'''
