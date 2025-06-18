import sys
import unittest
import json
import yaml

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
        """
        actual = gardener.machine_images_for_cloud_profile(yaml.safe_load(sample_data))
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

        actual = gardener.machine_images_for_cloud_profile(yaml.safe_load(sample_data), cris=cri_mapping)
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

        actual = gardener.machine_images_for_cloud_profile(yaml.safe_load(sample_data), compatibilities=compat_mapping)
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
