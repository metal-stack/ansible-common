import os

MODULES_PATH = os.path.join(os.path.dirname(os.path.abspath(os.path.dirname(__file__))), 'library')
MODULE_UTILS_PATH = os.path.join(os.path.dirname(os.path.abspath(os.path.dirname(__file__))), 'module_utils')
FILTER_PLUGINS_PATH = os.path.join(os.path.dirname(os.path.abspath(os.path.dirname(__file__))), 'filter_plugins')
ACTION_PLUGINS_PATH = os.path.join(os.path.dirname(os.path.abspath(os.path.dirname(__file__))), 'action_plugins')


def read_mock_file(name):
    with open(os.path.join(os.path.dirname(__file__), "mock", name), 'r') as f:
        return f.read()
