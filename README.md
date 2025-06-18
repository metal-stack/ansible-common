# ⚠️ This repository has been archived. Please migrate to [metal-ansible-collections](https://github.com/metal-stack/metal-ansible-collections)!

# Ansible Common

This repository contains shared roles, modules and plugins for metal-stack.

<!-- TOC depthfrom:2 depthto:6 withlinks:true updateonsave:true orderedlist:false -->

- [Modules](#modules)
- [Roles](#roles)
- [Filter Plugins](#filter-plugins)
- [Usage](#usage)

<!-- /TOC -->

## Modules

| Module Name                         | Description                                                  | Requirements |
| ----------------------------------- | ------------------------------------------------------------ | ------------ |
| [setup_yaml](library/setup_yaml.py) | Setup plugin that resolves variables from a remote YAML file |              |

## Roles

| Role Name                                                              | Description                                                                                                           |
| ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| [docker-over-tcp](roles/docker-over-tcp)                               | Exposes the Docker socket via TCP                                                                                     |
| [gcp-auth](roles/gcp-auth)                                             | Authenticates at Google Cloud                                                                                         |
| [gcp-create](roles/gcp-create)                                         | Creates a Kubernetes cluster at Google Cloud                                                                          |
| [gcp-destroy](roles/gcp-destroy)                                       | Destroys a Kubernetes cluster at Google Cloud                                                                         |
| [group-k8s](roles/group-k8s)                                           | Dynamically creates groups called `k8s-masters` and `k8s-workers` from vars defined `master_nodes` and `worker_nodes` |
| [helm-chart](roles/helm-chart)                                         | Deploys a helm chart to a k8s cluster                                                                                 |
| [systemd-docker-service](roles/systemd-docker-service)                 | Renders a systemd unit file that runs an application within a docker container                                        |
| [systemd-docker-service-cleanup](roles/systemd-docker-service-cleanup) | Stops a systemd unit and deletes its service definition                                                               |

## Filter Plugins

| Plugin Name               | Requirements                                                               | Description                                                           |
| ------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| humanfriendly             | [humanfriendly](https://github.com/xolox/python-humanfriendly)             | Converts sizes into human-friendly formats                            |
| transpile_ignition_config | [ct](https://github.com/coreos/container-linux-config-transpiler/releases) | Transforming a human-friendly Container Linux Config into a JSON file |
| metal_lb_config           |                                                                            | Generates the config map for metal-lb                                 |
| shoot_admin_kubeconfig    |                                                                            | Generates a kubeconfig for a namespace and shoot name.                |

## Usage

It's convenient to use ansible-galaxy in order to use this project. For your project, set up a `requirements.yml`:

```yaml
- src: https://github.com/metal-stack/ansible-common.git
  name: ansible-common
  version: v0.6.1
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
