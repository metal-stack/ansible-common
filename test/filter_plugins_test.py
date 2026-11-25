import sys
import unittest
import base64
import json
import yaml

from unittest.mock import patch

from test import FILTER_PLUGINS_PATH, read_mock_file

sys.path.insert(0, FILTER_PLUGINS_PATH)
import common
import gcp
import gardener


class UtilsFilterTest(unittest.TestCase):
    def test_all_filters_present(self):
        for expected_filter in ["metal_lb_conf", "humanfriendly", "transpile_ignition_config"]:
            self.assertIn(expected_filter, common.FilterModule().filters())

        for expected_filter in ["extract_gcp_node_network"]:
            self.assertIn(expected_filter, gcp.FilterModule().filters())


class HumanfriendlyTest(unittest.TestCase):
    def test_parsing_size(self):
        actual = common.parse_size("1MB", binary=False)

        expected = 1000000

        self.assertEqual(expected, actual)

    def test_parsing_size_binary(self):
        actual = common.parse_size("1KB", binary=True)

        expected = 1024

        self.assertEqual(expected, actual)


class GCPTest(unittest.TestCase):
    def test_extract_gcp_node_network(self):
        subnets = json.loads(read_mock_file("gke_container_subnets.json"))

        actual = gcp.extract_gcp_node_network(subnets, "europe-west3")

        self.assertEqual("0.0.0.3/32", actual)


class CloudProfileImageTest(unittest.TestCase):
    def test_image_list(self):
        self.maxDiff = None

        sample_data = """
        - id: firewall-ubuntu-2.0.20200714
          name: Firewall 2 Ubuntu 20200714
          description: Firewall 2 Ubuntu 20200714
          url: http://images.metal-stack.io/metal-os/master/firewall/2.0-ubuntu/20200714/img.tar.lz4
          features:
            - firewall
            - machine
        - id: firewall-2.0.20200714
          name: Firewall 2 Debian 20200714
          description: Firewall 2 Debian 20200714
          url: http://images.metal-stack.io/metal-os/master/firewall/2.0/20200714/img.tar.lz4
          features:
            - firewall
        - id: ubuntu-19.10.20200331
          name: Ubuntu 19.10 20200331
          description: Ubuntu 19.10 20200331
          url: http://images.metal-stack.io/metal-os/ubuntu/19.10/20200331/img.tar.lz4
          features:
            - machine
        - id: ubuntu-19.10.20200701
          name: Ubuntu 19.10 20200701
          description: Ubuntu 19.10 20200701
          url: http://images.metal-stack.io/metal-os/ubuntu/19.10/20200701/img.tar.lz4
          features:
            - machine
        - id: ubuntu-20.04.20200331
          name: Ubuntu 20.04 20200331
          description: Ubuntu 20.04 20200331
          url: http://images.metal-stack.io/metal-os/ubuntu/20.04/20200331/img.tar.lz4
          features:
            - machine
        - id: debian-10.0.20200331
          name: Debian 10.0.20200331
          description: Debian 10 20200331
          url: http://images.metal-stack.io/metal-os/debian/10/20200331/img.tar.lz4
          features:
            - machine
        - id: centos-7.0.20210620
          name: Centos 7 20210620
          description: Centos 7 20210620
          url: http://images.metal-stack.io/metal-os/master/centos/7/20210620/img.tar.lz4
          omit_from_cloud_profile: yes
          features:
              - machine
        # v2 images
        - id: ubuntu-26.4
          meta:
              labels: {}
          url: https://images.metal-stack.io/metal-os/stable/ubuntu/26.04/img.tar.lz4
          name: Ubuntu 26.04
          description: Ubuntu 26.04 Latest Release
          features:
              - IMAGE_FEATURE_MACHINE
          classification: IMAGE_CLASSIFICATION_PREVIEW
        """
        actual = gardener.machine_images_for_cloud_profile(
            yaml.safe_load(sample_data))
        expected = [
            {
                "name": "firewall-ubuntu",
                "versions": [
                    {"version": "2.0"},
                    {"version": "2.0.20200714"},
                ]
            },
            {
                "name": "ubuntu",
                "versions": [
                    {"version": "19.10"},
                    {"version": "19.10.20200331"},
                    {"version": "19.10.20200701"},
                    {"version": "20.04"},
                    {"version": "20.04.20200331"},
                    {"version": "26.4"},
                ],
            },
            {
                "name": "debian",
                "versions": [
                    {"version": "10.0"},
                    {"version": "10.0.20200331"},
                ],
            },
        ]

        self.assertListEqual(actual, expected)

    def test_image_list_with_cri_mapping(self):
        self.maxDiff = None

        sample_data = """
        - id: firewall-ubuntu-2.0.20200714
          name: Firewall 2 Ubuntu 20200714
          description: Firewall 2 Ubuntu 20200714
          url: http://images.metal-stack.io/metal-os/master/firewall/2.0-ubuntu/20200714/img.tar.lz4
          features:
            - firewall
            - machine
        - id: firewall-2.0.20200714
          name: Firewall 2 Debian 20200714
          description: Firewall 2 Debian 20200714
          url: http://images.metal-stack.io/metal-os/master/firewall/2.0/20200714/img.tar.lz4
          features:
            - firewall
        - id: ubuntu-19.10.20200331
          name: Ubuntu 19.10 20200331
          description: Ubuntu 19.10 20200331
          url: http://images.metal-stack.io/metal-os/ubuntu/19.10/20200331/img.tar.lz4
          features:
            - machine
        - id: ubuntu-19.10.20200701
          name: Ubuntu 19.10 20200701
          description: Ubuntu 19.10 20200701
          url: http://images.metal-stack.io/metal-os/ubuntu/19.10/20200701/img.tar.lz4
          features:
            - machine
        - id: ubuntu-20.04.20200331
          name: Ubuntu 20.04 20200331
          description: Ubuntu 20.04 20200331
          url: http://images.metal-stack.io/metal-os/ubuntu/20.04/20200331/img.tar.lz4
          features:
            - machine
        """

        cris = [
            {
                "name": "containerd",
                "containerRuntimes": [
                    {"type": "gvisor"},
                    {"type": "kata-containers"},
                ],
            }
        ]
        cri_mapping = {
            "ubuntu": {
                "when": {
                    "operator": ">=",
                    "version": "20.04",
                },
                "cris": cris,
            }
        }

        actual = gardener.machine_images_for_cloud_profile(
            yaml.safe_load(sample_data), cris=cri_mapping)
        expected = [
            {
                "name": "firewall-ubuntu",
                "versions": [
                    {"version": "2.0"},
                    {"version": "2.0.20200714"},
                ]
            },
            {
                "name": "ubuntu",
                "versions": [
                    {"version": "19.10"},
                    {"version": "19.10.20200331"},
                    {"version": "19.10.20200701"},
                    {
                        "version": "20.04",
                        "cri": [
                            {
                                "name": "containerd",
                                "containerRuntimes": [
                                    {"type": "gvisor"},
                                    {"type": "kata-containers"},
                                ],
                            }
                        ],
                    },
                    {
                        "version": "20.04.20200331",
                        "cri": [
                            {
                                "name": "containerd",
                                "containerRuntimes": [
                                    {"type": "gvisor"},
                                    {"type": "kata-containers"},
                                ],
                            }
                        ],
                    },
                ],
            },
        ]

        self.assertListEqual(actual, expected)

    def test_image_list_with_compatibility_mapping(self):
        self.maxDiff = None

        sample_data = """
        - id: debian-12.0.20240101
          name: Debian 12 20240101
          description: Debian 12 20240101
          url: http://images.metal-stack.io/metal-os/debian/12/img.tar.lz4
          features:
            - machine
        - id: debian-12.0.20250231
          name: Debian 12 20250231
          description: Debian 12 20250231
          url: http://images.metal-stack.io/metal-os/debian/12/img.tar.lz4
          features:
            - machine
        """

        compat_mapping = {
            "debian": {
                "when": {
                    "operator": "<",
                    "version": "12.0.20250101",
                    "except": ["12.0"],
                },
                "kubelet": "<= 1.30",
            }
        }

        actual = gardener.machine_images_for_cloud_profile(
            yaml.safe_load(sample_data), compatibilities=compat_mapping)
        expected = [
            {
                "name": "debian",
                "versions": [
                    {
                        "version": "12.0",
                    },
                    {
                        "version": "12.0.20240101",
                        "kubeletVersionConstraint": "<= 1.30"
                    },
                    {
                        "version": "12.0.20250231",
                    },
                ],
            },
        ]

        self.assertListEqual(actual, expected)


class LegacyHttpResponse(object):
    def __init__(self, data):
        self.data = data


class LegacyApiClient(object):
    """Mimics kubernetes python clients < 37.0.0."""

    def __init__(self, response_data):
        self.response_data = response_data
        self.calls = []

    def call_api(self, resource_path, method,
                 path_params=None, query_params=None, header_params=None,
                 body=None, post_params=None, files=None,
                 response_type=None, auth_settings=None, async_req=None,
                 _return_http_data_only=None, collection_formats=None,
                 _preload_content=True, _request_timeout=None, _host=None):
        self.calls.append(dict(
            resource_path=resource_path,
            method=method,
            body=body,
            auth_settings=auth_settings,
            _return_http_data_only=_return_http_data_only,
            _preload_content=_preload_content,
        ))
        return LegacyHttpResponse(self.response_data)


class ModernHttpResponse(object):
    def __init__(self, data):
        self.data = data
        self.read_called = False

    def read(self):
        self.read_called = True
        return self.data


class ModernApiClient(object):
    """Mimics kubernetes python clients >= 37.0.0."""

    def __init__(self, response_data):
        self.response_data = response_data
        self.host = "https://garden.example.com"
        self.serialized = None
        self.calls = []

    def param_serialize(self, method, resource_path,
                        path_params=None, query_params=None, header_params=None,
                        body=None, post_params=None, files=None, auth_settings=None,
                        collection_formats=None, _host=None, _request_auth=None):
        self.serialized = dict(
            method=method,
            resource_path=resource_path,
            header_params=header_params,
            body=body,
            auth_settings=auth_settings,
        )
        return method, self.host + resource_path, header_params, body, post_params

    def call_api(self, method, url, header_params=None, body=None,
                 post_params=None, _request_timeout=None):
        self.calls.append(dict(
            method=method,
            url=url,
            header_params=header_params,
            body=body,
        ))
        response = ModernHttpResponse(self.response_data)
        self.response = response
        return response


class ShootAdminKubeconfigTest(unittest.TestCase):
    def test_post_with_legacy_api_client(self):
        api = LegacyApiClient(b'{"status": {"kubeconfig": "abc"}}')

        actual = gardener._post(api, "/apis/test", {"spec": {}})

        self.assertEqual(b'{"status": {"kubeconfig": "abc"}}', actual)
        self.assertEqual(1, len(api.calls))
        self.assertEqual("/apis/test", api.calls[0]["resource_path"])
        self.assertEqual("POST", api.calls[0]["method"])
        self.assertEqual({"spec": {}}, api.calls[0]["body"])
        self.assertEqual(["BearerToken"], api.calls[0]["auth_settings"])
        self.assertTrue(api.calls[0]["_return_http_data_only"])
        self.assertFalse(api.calls[0]["_preload_content"])

    def test_post_with_modern_api_client(self):
        api = ModernApiClient(b'{"status": {"kubeconfig": "abc"}}')

        actual = gardener._post(api, "/apis/test", {"spec": {}})

        self.assertEqual(b'{"status": {"kubeconfig": "abc"}}', actual)
        self.assertTrue(api.response.read_called)
        self.assertEqual("POST", api.serialized["method"])
        self.assertEqual("/apis/test", api.serialized["resource_path"])
        self.assertEqual({"spec": {}}, api.serialized["body"])
        self.assertEqual(["BearerToken"], api.serialized["auth_settings"])
        self.assertEqual("application/json", api.serialized["header_params"]["Accept"])
        self.assertEqual("application/json", api.serialized["header_params"]["Content-Type"])
        self.assertEqual(1, len(api.calls))
        self.assertEqual("POST", api.calls[0]["method"])
        self.assertEqual("https://garden.example.com/apis/test", api.calls[0]["url"])

    def test_shoot_admin_kubeconfig(self):
        admin_kubeconfig = yaml.safe_dump({
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [],
            "contexts": [],
            "users": [],
            "current-context": "",
        })
        response_data = json.dumps({
            "status": {
                "kubeconfig": base64.b64encode(admin_kubeconfig.encode("utf-8")).decode("utf-8"),
            },
        }).encode("utf-8")
        api = ModernApiClient(response_data)

        with patch.object(gardener.config, "load_kube_config_from_dict"), \
                patch.object(gardener.client, "ApiClient", return_value=api):
            actual = gardener.shoot_admin_kubeconfig("apiVersion: v1\nkind: Config\n", "garden-test", "shoot-1")

        self.assertEqual(admin_kubeconfig, actual)
        self.assertEqual("POST", api.serialized["method"])
        self.assertEqual(
            "/apis/core.gardener.cloud/v1beta1/namespaces/garden-test/shoots/shoot-1/adminkubeconfig",
            api.serialized["resource_path"])
        self.assertEqual({"expirationSeconds": 28800}, api.serialized["body"]["spec"])
