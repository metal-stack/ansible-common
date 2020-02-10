# Ansible Common

This repository contains shared roles, modules and plugins for Metal Stack.

<!-- TOC depthFrom:2 depthTo:6 withLinks:1 updateOnSave:1 orderedList:0 -->

- [Modules](#modules)
- [Roles](#roles)
- [Dynamic Inventories](#dynamic-inventories)
- [Filter Plugins](#filter-plugins)
- [Usage](#usage)

<!-- /TOC -->

## Modules

| Module Name                               | Description                          | Requirements      |
| ----------------------------------------- | ------------------------------------ | ----------------- |
| [metal_ip](library/metal_ip.py)           | Manages Metal Stack IP entities      | metalctl (binary) |
| [metal_network](library/metal_network.py) | Manages Metal Stack network entities | metalctl (binary) |

## Roles

| Role Name                                | Description                                                                                                           |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| [docker-over-tcp](roles/docker-over-tcp) | Exposes the Docker socket via TCP                                                                                     |
| [gcp-auth](roles/gcp-auth)               | Authenticates at Google Cloud                                                                                         |
| [gcp-create](roles/gcp-create)           | Creates a Kubernetes cluster at Google Cloud                                                                          |
| [gcp-destroy](roles/gcp-destroy)         | Destroys a Kubernetes cluster at Google Cloud                                                                         |
| [group-k8s](roles/group-k8s)             | Dynamically creates groups called `k8s-masters` and `k8s-workers` from vars defined `master_nodes` and `worker_nodes` |
| [helm](roles/helm)                       | Deploys [helm](https://helm.sh/)                                                                                      |
| [helm-chart](roles/helm-chart)           | Deploys a helm chart to a k8s cluster                                                                                 |
| [metal-k8s-fixes](roles/metal-k8s-fixes) | Patches for deploying K8s on Metal when using the gerrlingguy Kubernetes role                                         |
| [vagrant-prep](roles/vagrant-prep)       | Typical preparation for Vagrant machines prior to a Metal Stack deployment                                            |

## Dynamic Inventories

| Inventory Name               | Description                                          |
| ---------------------------- | ---------------------------------------------------- |
| [Vagrant](inventory/vagrant) | Builds a dynamic inventory from Vagrant's ssh-config |
| [Metal](inventory/metal)     | Dynamic inventory from Metal Stack                   |

## Filter Plugins

| Plugin Name               | Requirements                                                               | Description                                                           |
| ------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| humanfriendly             | [humanfriendly](https://github.com/xolox/python-humanfriendly)             | Converts sizes into human-friendly formats                            |
| transpile_ignition_config | [ct](https://github.com/coreos/container-linux-config-transpiler/releases) | Transforming a human-friendly Container Linux Config into a JSON file |
| metal_lb_config           |                                                                            | Generates the config map for metal-lb                                 |

## Usage

It's convenient to use ansible-galaxy in order to use this project. For your project, set up a `requirements.yml`:

```yaml
- src: https://github.com/metal-stack/ansible-common.git
  name: ansible-common
  version: v0.4.0
```

You can then download the roles with the following command:

```bash
ansible-galaxy install -r requirements.yml
```

Then reference the roles in your playbooks like this:

```yaml
- name: Deploy something
  hosts: localhost
  connection: local
  gather_facts: no
  roles:
    - name: ansible-common/roles/helm-chart
      vars:
        ...
```
