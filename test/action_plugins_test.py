import sys
import unittest
from ansible.template import Templar
from ansible.parsing.dataloader import DataLoader

from test import ACTION_PLUGINS_PATH
from mock import patch, MagicMock, call
from ansible.playbook.task import Task

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

SAMPLE_VECTOR_02 = """
vectors:
  metal-stack:
    url: https://raw.githubusercontent.com/metal-stack/releases/master/release.yaml

docker-images:
  metal-stack:
    control-plane:
      masterdata-api:
        name: metalstack/masterdata-api
        tag: v0.7.1
"""

SAMPLE_VECTOR_03 = """
vectors:
  metal-stack:
    url: https://raw.githubusercontent.com/metal-stack/releases/master/nested.yaml

docker-images:
  metal-stack:
    control-plane:
      metal-console:
        name: metalstack/metal-console
        tag: v0.4.2
"""


def open_url_mock(return_value, return_code=200):
    m = MagicMock()
    m.getcode.return_value = return_code
    m.read.return_value = return_value
    m.__enter__.return_value = m
    return m


class MetalReleaseTest(unittest.TestCase):
    def setUp(self):
        self.task = MagicMock(Task)
        self.play_context = MagicMock()
        self.play_context.check_mode = False
        self.connection = MagicMock()
        self.loader = DataLoader()
        self.templar = Templar(loader=self.loader)

        self.maxDiff = None

    def tearDown(self):
        self.task = None
        self.play_context = None
        self.connection = None

    def initModule(self, args):
        self.task.action = "setup_yaml"
        self.task.async_val = False
        self.task.args = args
        return ActionModule(self.task, self.connection, self.play_context, loader=self.loader, templar=self.templar,
                            shared_loader_obj=None)

    @patch("setup_yaml.open_url")
    def test_resolves(self, mock):
        mock.return_value = open_url_mock(SAMPLE_VECTOR_01)
        module_args = dict(
            files=[
                dict(
                    url="https://raw.githubusercontent.com/metal-stack/releases/master/release.yaml",
                    mapping=dict(metal_api_image_tag="docker-images.metal-stack.control-plane.metal-api.tag"),
                ),
            ],
        )
        task_vars = dict()
        module = self.initModule(args=module_args)

        actual = module.run(tmp=None, task_vars=task_vars)

        mock.assert_called()
        mock.assert_called_with('https://raw.githubusercontent.com/metal-stack/releases/master/release.yaml')

        expected = dict({
            'metal_api_image_tag': 'v0.7.8',
            module.ALREADY_RESOLVED_MARKER: True,
        })

        self.assertIn("ansible_facts", actual)
        self.assertEqual(expected, actual["ansible_facts"])

    @patch("setup_yaml.open_url")
    def test_nested_resolve(self, mock):
        mock.side_effect = [
            open_url_mock(SAMPLE_VECTOR_02),
            open_url_mock(SAMPLE_VECTOR_01)
        ]
        module_args = dict(
            files=[
                dict(
                    url="https://raw.githubusercontent.com/metal-stack/releases/master/nested.yaml",
                    mapping=dict(masterdata_api_image_tag="docker-images.metal-stack.control-plane.masterdata-api.tag"),
                    nested=[
                        dict(url_path="vectors.metal-stack.url",
                             mapping=dict(metal_api_image_tag="docker-images.metal-stack.control-plane.metal-api.tag")),
                    ],
                ),
            ],
        )
        task_vars = dict()
        module = self.initModule(args=module_args)

        actual = module.run(tmp=None, task_vars=task_vars)

        mock.assert_called()
        expected_calls = [
            call('https://raw.githubusercontent.com/metal-stack/releases/master/nested.yaml'),
            call('https://raw.githubusercontent.com/metal-stack/releases/master/release.yaml'),
        ]
        mock.assert_has_calls(expected_calls)

        expected = dict({
            'masterdata_api_image_tag': 'v0.7.1',
            'metal_api_image_tag': 'v0.7.8',
            module.ALREADY_RESOLVED_MARKER: True,
        })

        self.assertIn("ansible_facts", actual)
        self.assertEqual(expected, actual["ansible_facts"])

    @patch("setup_yaml.open_url")
    def test_doubly_nested_resolve(self, mock):
        mock.side_effect = [
            open_url_mock(SAMPLE_VECTOR_03),
            open_url_mock(SAMPLE_VECTOR_02),
            open_url_mock(SAMPLE_VECTOR_01)
        ]
        module_args = dict(
            files=[
                dict(
                    url="https://raw.githubusercontent.com/metal-stack/releases/master/doubly_nested.yaml",
                    mapping=dict(metal_console_image_tag="docker-images.metal-stack.control-plane.metal-console.tag"),
                    nested=[
                        dict(
                            url_path="vectors.metal-stack.url",
                            mapping=dict(
                                masterdata_api_image_tag="docker-images.metal-stack.control-plane.masterdata-api.tag"),
                            nested=[
                                dict(
                                    url_path="vectors.metal-stack.url",
                                    mapping=dict(
                                        metal_api_image_tag="docker-images.metal-stack.control-plane.metal-api.tag"
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
        task_vars = dict()
        module = self.initModule(args=module_args)

        actual = module.run(tmp=None, task_vars=task_vars)

        mock.assert_called()
        expected_calls = [
            call('https://raw.githubusercontent.com/metal-stack/releases/master/doubly_nested.yaml'),
            call('https://raw.githubusercontent.com/metal-stack/releases/master/nested.yaml'),
            call('https://raw.githubusercontent.com/metal-stack/releases/master/release.yaml'),
        ]
        mock.assert_has_calls(expected_calls)

        expected = dict({
            'metal_console_image_tag': 'v0.4.2',
            'masterdata_api_image_tag': 'v0.7.1',
            'metal_api_image_tag': 'v0.7.8',
            module.ALREADY_RESOLVED_MARKER: True,
        })

        self.assertIn("ansible_facts", actual)
        self.assertEqual(expected, actual["ansible_facts"])

    @patch("setup_yaml.open_url")
    def test_nested_resolve_through_magic_vars(self, mock):
        mock.side_effect = [
            open_url_mock(SAMPLE_VECTOR_02),
            open_url_mock(SAMPLE_VECTOR_01)
        ]
        module_args = dict(
            files=[
                dict(
                    url="https://raw.githubusercontent.com/metal-stack/releases/master/nested.yaml",
                    meta_var="nested_var"
                ),
            ],
        )
        task_vars = dict(
            nested_var=dict(
                mapping=dict(masterdata_api_image_tag="docker-images.metal-stack.control-plane.masterdata-api.tag"),
                nested=[
                    dict(url_path="vectors.metal-stack.url",
                         meta_var="nested_var2"),
                ],
            ),
            nested_var2=dict(
                mapping=dict(
                    metal_api_image_tag="docker-images.metal-stack.control-plane.metal-api.tag"
                ),
            ),
        )
        module = self.initModule(args=module_args)

        actual = module.run(tmp=None, task_vars=task_vars)

        mock.assert_called()
        expected_calls = [
            call('https://raw.githubusercontent.com/metal-stack/releases/master/nested.yaml'),
            call('https://raw.githubusercontent.com/metal-stack/releases/master/release.yaml'),
        ]
        mock.assert_has_calls(expected_calls)

        expected = dict({
            'masterdata_api_image_tag': 'v0.7.1',
            'metal_api_image_tag': 'v0.7.8',
            module.ALREADY_RESOLVED_MARKER: True,
        })

        self.assertIn("ansible_facts", actual)
        self.assertEqual(expected, actual["ansible_facts"])

    @patch("setup_yaml.open_url")
    def test_nested_resolve_no_recursive(self, mock):
        mock.side_effect = [
            open_url_mock(SAMPLE_VECTOR_02),
            open_url_mock(SAMPLE_VECTOR_01)
        ]
        module_args = dict(
            files=[
                dict(
                    url="https://raw.githubusercontent.com/metal-stack/releases/master/nested.yaml",
                    mapping=dict(masterdata_api_image_tag="docker-images.metal-stack.control-plane.masterdata-api.tag"),
                    nested=[
                        dict(url_path="vectors.metal-stack.url",
                             mapping=dict(metal_api_image_tag="docker-images.metal-stack.control-plane.metal-api.tag")),
                    ],
                    recursive=False,
                ),
            ],
        )
        task_vars = dict()
        module = self.initModule(args=module_args)

        actual = module.run(tmp=None, task_vars=task_vars)

        mock.assert_called()
        expected_calls = [
            call('https://raw.githubusercontent.com/metal-stack/releases/master/nested.yaml'),
        ]
        mock.assert_has_calls(expected_calls)

        expected = dict({
            'masterdata_api_image_tag': 'v0.7.1',
            module.ALREADY_RESOLVED_MARKER: True,
        })

        self.assertIn("ansible_facts", actual)
        self.assertEqual(expected, actual["ansible_facts"])

    @patch("setup_yaml.open_url")
    def test_resolves_not_overriding_existing_vars(self, mock):
        mock.return_value = open_url_mock(SAMPLE_VECTOR_01)
        module_args = dict(
            files=[
                dict(
                    url="https://raw.githubusercontent.com/metal-stack/releases/master/release.yaml",
                    mapping=dict(metal_api_image_tag="docker-images.metal-stack.control-plane.metal-api.tag"),
                ),
            ],
        )
        task_vars = dict(
            metal_api_image_tag='v0.0.1',
        )
        module = self.initModule(args=module_args)

        actual = module.run(tmp=None, task_vars=task_vars)

        mock.assert_called()
        mock.assert_called_with('https://raw.githubusercontent.com/metal-stack/releases/master/release.yaml')

        expected = dict({
            module.ALREADY_RESOLVED_MARKER: True,
        })

        self.assertIn("ansible_facts", actual)
        self.assertEqual(expected, actual["ansible_facts"])
