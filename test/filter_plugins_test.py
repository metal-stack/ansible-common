import sys
import unittest
import json

from test import FILTER_PLUGINS_PATH, read_mock_file

sys.path.insert(0, FILTER_PLUGINS_PATH)
import common
import gcp

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
