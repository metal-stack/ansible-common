#!/usr/bin/env python

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from kubernetes import config, dynamic
from kubernetes.client.rest import ApiException
from ansible.module_utils.basic import AnsibleModule


def run_module():
    module_args = dict(
        api_version=dict(type='str', required=False),
        kind=dict(type='str', required=False),
        kubeconfig=dict(type='raw', no_log=True, required=False),
    )

    result = dict(
        changed=False,
        result=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if module.check_mode:
        module.exit_json(**result)

    kubeconfig = module.params.get('kubeconfig')

    if isinstance(kubeconfig, str) or kubeconfig is None:
        api_client = config.new_client_from_config(config_file=kubeconfig)
    elif isinstance(kubeconfig, dict):
        api_client = config.new_client_from_config_dict(config_dict=kubeconfig)
    else:
        module.fail_json(msg="Error while reading kubeconfig parameter - a string or dict expected, but got %s instead" % type(kubeconfig), **result)

    dynamic_client = dynamic.DynamicClient(client=api_client)

    api_version = module.params.get('api_version', None)
    kind = module.params.get('kind', None)

    try:
        api_response = dynamic_client.resources.search(api_version=api_version, kind=kind)
    except ApiException as e:
        module.fail_json(msg="Exception when searching discovery api: %s\n" % e, **result)

    resources = []

    for resource in api_response:
        subresources = []
        if resource.subresources:
            for name, _ in resource.subresources.items():
                subresources.append(name)

        resources.append(dict(
            api_version=resource.api_version,
            kind=resource.kind,
            group=resource.group,
            name=resource.name,
            singular_name=resource.singular_name,
            namespaced=resource.namespaced,
            short_names=resource.short_names,
            verbs=resource.verbs,
            subresources=subresources,
        ))

    result["result"] = resources

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
