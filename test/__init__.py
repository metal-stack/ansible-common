import mock
import os
import json
import unittest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes

MODULES_PATH = os.path.join(os.path.dirname(os.path.abspath(os.path.dirname(__file__))), 'library')
MODULE_UTILS_PATH = os.path.join(os.path.dirname(os.path.abspath(os.path.dirname(__file__))), 'module_utils')
FILTER_PLUGINS_PATH = os.path.join(os.path.dirname(os.path.abspath(os.path.dirname(__file__))), 'filter_plugins')
ACTION_PLUGINS_PATH = os.path.join(os.path.dirname(os.path.abspath(os.path.dirname(__file__))), 'action_plugins')


def set_module_args(args):
    """prepare arguments so that they will be picked up during module creation"""
    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case"""

    def __init__(self, kwargs):
        self.module_results = kwargs
        super(AnsibleExitJson, self).__init__(kwargs)


class AnsibleFailJson(Exception):
    """Exception class to be raised by module.fail_json and caught by the test case"""

    def __init__(self, kwargs):
        self.module_results = kwargs
        super(AnsibleFailJson, self).__init__(kwargs)


def exit_json(_, **kwargs):
    """function to patch over exit_json; package return data into an exception"""
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(_, **kwargs):
    """function to patch over fail_json; package return data into an exception"""
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


class AnsibleCommon(unittest.TestCase):
    def defaultSetUpTasks(self):
        modules = {
            'ansible.module_utils.metal': metal,
        }
        self.module_patcher = mock.patch.dict('sys.modules', modules)
        self.module_patcher.start()
        self.addCleanup(self.module_patcher.stop)

        self.mock_module_helper = mock.patch.multiple(basic.AnsibleModule,
                                                      exit_json=exit_json,
                                                      fail_json=fail_json)
        self.mock_module_helper.start()
        self.addCleanup(self.mock_module_helper.stop)
