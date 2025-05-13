from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import base64
import yaml
import json

from kubernetes import config, client

from ansible.plugins.test.core import version_compare


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


def machine_images_for_cloud_profile(image_list, cris=None, compatibilities=None):
    images = dict()
    for image in image_list:
        if 'machine' not in image.get("features", list()):
            continue

        if image.get('omit_from_cloud_profile', False):
            continue

        image_id = image.get("id")
        if image_id is None:
            continue

        parts = image_id.split("-")
        name = "-".join(parts[:-1])

        version = parts[-1]

        version_parts = version.split(".")
        # ubuntu-19.10.20200331
        # major = version_parts[0]
        minor = ".".join(version_parts[:2])

        image_versions = images.get(name, set())
        # Do not add the major version to the vector
        # metal-api cannot match latest version if only major is given
        # image_versions.add(major)
        image_versions.add(minor)
        image_versions.add(version)
        images[name] = image_versions

    result = list()
    for name, value in images.items():
        versions = list()
        for v in sorted(list(value)):
            version = dict(
                version=v
            )

            if cris is not None and name in cris:
                cri = cris[name].copy()
                cri_config = cri.pop("cris", [])
                cri_condition = cri.pop("when", None)

                if cri_condition is None:
                    version["cri"] = cri_config
                else:
                    if v in cri_condition.get("except", []):
                        pass
                    else:
                        if version_compare(v, cri_condition["version"], cri_condition["operator"]):
                            version["cri"] = cri_config

            if compatibilities is not None and name in compatibilities:
                compat = compatibilities[name].copy()

                kubelet = compat.pop("kubelet")
                condition = compat.pop("when", None)

                if condition is None:
                    version["kubeletVersionConstraint"] = kubelet
                else:
                    if v in condition.get("except", []):
                        pass
                    else:
                        if version_compare(v, condition["version"], condition["operator"]):
                            version["kubeletVersionConstraint"] = kubelet

            versions.append(version)

        image = dict(
            name=name,
            versions=versions,
        )
        result.append(image)

    return result


class FilterModule(object):
    def filters(self):
        return {
            'shoot_admin_kubeconfig': shoot_admin_kubeconfig,
            'machine_images_for_cloud_profile': machine_images_for_cloud_profile,
        }
