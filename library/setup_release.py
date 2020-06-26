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
module: setup_release
short_description: Resolves variables from a remote YAML file
version_added: "2.9"
description:
    - This module downloads a YAML file and maps contents of it to ansible_facts according to a given variable mapping. 
    - Within a YAML file, it is also possible to point to other YAML files, which will then be resolved recursively.
    - This module picks up some variables "magically", which makes the module very versatile and easy to read
      but also causes some conventions that need to be followed when using this module. 
    - Please check out the examples of how to use it.
options:
    releases:
        description:
            - A list of releases to be resolved.
            - The module will just skip if this variable is not provided.
            - This parameter can be "magically" provided by defining the variable `setup_release`
        required: false
    smart:
        description:
            - Will make this module skip in case it was already executed. 
              Sets a marker into the vars to prevent repeated execution.
            - This parameter can be "magically" provided by defining the variable `setup_release_smart`
        required: false
        default: true
    recursive:
        description:
            - Can be used to disable recursive resolution of other release vectors. This can be useful for development 
              purposes in case yu want to use different versions than defined (development purposes).
        required: false
        default: true
author:
    - metal-stack
notes:
    - We typically use this module for dynamically providing docker image version variables to ansible roles. This 
      explains the name of the module. Often, we also call the contents of the downloaded YAML file a release vector.
'''

EXAMPLES = '''
# Assume a YAML file containing release versions of docker-images at https://example.com/v1.0.0/example.yaml:
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
  setup_release:
    releases:
      - name: example
        version: v1.0.0
        info:
          url_template: https://example.com/%s/example.yaml
          mapping:
            hello_world_image_tag: "docker-images.hello-world.tag"
        
# The module can now do its job. The expected output will be:
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
# setup_release:
#   - name: example
#     version: v1.0.0
#
# example_release:
#  url_template: https://example.com/%s/example.yaml
#  mapping:
#    hello_world_image_tag: "docker-images.hello-world.tag"
# ...
#
# You could then also just write the task definition like this:

- name: gather release versions
  setup_release:

# For the "magic" lookup of the release info, the module tries to find a variable composed from the release name.
# The expected variable has the name of the release with `_release` as a postfix. Hyphens will be replaced by 
# underscores.
#
# The "magic" lookup is extremely helpful because release infos can be defined anywhere else, e.g. from external roles.
'''
