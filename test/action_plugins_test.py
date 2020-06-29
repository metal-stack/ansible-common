import sys
import unittest

from test import ACTION_PLUGINS_PATH
from mock import patch, MagicMock, call

sys.path.insert(0, ACTION_PLUGINS_PATH)
from setup_yaml import ActionModule

SAMPLE_VECTOR_01 = """
docker-images:
  metal-stack:
    control-plane:
      metal-api:
        name: metalstack/metal-api
        tag: v0.7.8
"""

SAMPLE_VECTOR_NESTED = """
vectors:
  metal-stack:
    url_template: https://raw.githubusercontent.com/metal-stack/releases/%s/release.yaml
    version: master

docker-images:
  metal-stack:
    control-plane:
      masterdata-api:
        name: metalstack/masterdata-api
        tag: v0.7.1
"""


class MetalReleaseTest(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    @patch("setup_yaml.open_url")
    def test_resolves(self, mock):
        m = MagicMock()
        m.getcode.return_value = 200
        m.read.return_value = SAMPLE_VECTOR_01
        m.__enter__.return_value = m
        mock.return_value = m

        module = ActionModule(None, None, None, None, None, None)
        actual = module.resolve(
            "https://raw.githubusercontent.com/metal-stack/releases/%s/release.yaml",
            "master",
            dict(metal_api_image_tag="docker-images.metal-stack.control-plane.metal-api.tag"),
            [],
            dict(),
            dict(),
        )

        mock.assert_called()
        mock.assert_called_with('https://raw.githubusercontent.com/metal-stack/releases/master/release.yaml')

        expected = dict({
            'ansible_facts': {
                'metal_api_image_tag': 'v0.7.8',
                module.ALREADY_RESOLVED_MARKER: True,
            }
        })

        self.assertEqual(expected, actual)

    @patch("setup_yaml.open_url")
    def test_nested_resolve(self, mock):
        m1 = MagicMock()
        m1.getcode.return_value = 200
        m1.__enter__.return_value = m1
        m1.read.return_value = SAMPLE_VECTOR_NESTED

        m2 = MagicMock()
        m2.getcode.return_value = 200
        m2.__enter__.return_value = m1
        m2.read.return_value = SAMPLE_VECTOR_01

        mock.side_effect = [m1, m2]

        module = ActionModule(None, None, None, None, None, None)
        actual = module.resolve(
            "https://raw.githubusercontent.com/metal-stack/releases/%s/nested.yaml",
            "master",
            dict(masterdata_api_image_tag="docker-images.metal-stack.control-plane.masterdata-api.tag"),
            [
                dict(url_template_path="vectors.metal-stack.url_template",
                     version_path="vectors.metal-stack.version",
                     mapping_var="nested_mapping",
                     nested=dict()),
            ],
            dict(
                nested_mapping=dict(metal_api_image_tag="docker-images.metal-stack.control-plane.metal-api.tag"),
            ),
            dict(),
        )

        mock.assert_called()
        expected_calls = [
            call('https://raw.githubusercontent.com/metal-stack/releases/master/nested.yaml'),
            call('https://raw.githubusercontent.com/metal-stack/releases/master/release.yaml'),
        ]
        mock.assert_has_calls(expected_calls)

        expected = dict({
            'ansible_facts': {
                'masterdata_api_image_tag': 'v0.7.1',
                'metal_api_image_tag': 'v0.7.8',
                module.ALREADY_RESOLVED_MARKER: True,
            }
        })

        self.assertEqual(expected, actual)
