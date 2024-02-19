from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import base64
import yaml
import json

from kubernetes import config, client


def shoot_admin_kubeconfig(kubeconfig, project_namespace, shoot_name, expiry_seconds=28800):
    data = yaml.safe_load(kubeconfig)

    configuration = client.Configuration()
    config.load_kube_config_from_dict(data, client_configuration=configuration)

    api = client.ApiClient(configuration=configuration)

    kubeconfig_request = {
        'apiVersion': 'authentication.gardener.cloud/v1alpha1',
        'kind': 'AdminKubeconfigRequest',
        'spec': {
        'expirationSeconds': expiry_seconds
        }
    }

    response = api.call_api(resource_path=f'/apis/core.gardener.cloud/v1beta1/namespaces/{project_namespace}/shoots/{shoot_name}/adminkubeconfig',
                            method='POST',
                            body=kubeconfig_request,
                            auth_settings=['BearerToken'],
                            _preload_content=False,
                            _return_http_data_only=True,
                        )

    return base64.b64decode(json.loads(response.data)["status"]["kubeconfig"]).decode('utf-8')


class FilterModule(object):
    def filters(self):
        return {
            'shoot_admin_kubeconfig': shoot_admin_kubeconfig,
        }
