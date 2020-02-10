import sys
import unittest

from test import FILTER_PLUGINS_PATH

sys.path.insert(0, FILTER_PLUGINS_PATH)
from common import parse_size
from common import FilterModule


class UtilsFilterTest(unittest.TestCase):
    def test_all_filters_present(self):
        filters = FilterModule().filters()

        expected_filters = ["metal_lb_conf", "humanfriendly", "transpile_ignition_config"]

        for expected_filter in expected_filters:
            self.assertIn(expected_filter, filters)


class HumanfriendlyTest(unittest.TestCase):
    def test_parsing_size(self):
        actual = parse_size("1MB", binary=False)

        expected = 1000000

        self.assertEqual(expected, actual)

    def test_parsing_size_binary(self):
        actual = parse_size("1KB", binary=True)

        expected = 1024

        self.assertEqual(expected, actual)
