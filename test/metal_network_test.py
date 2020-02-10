import sys
from mock import patch, call
from test import (
    AnsibleCommon,
    AnsibleFailJson,
    AnsibleExitJson,
    Mock,
    set_module_args,
    MODULES_PATH,
)

sys.path.insert(0, MODULES_PATH)


class TestMetal(AnsibleCommon):
    def setUp(self):
        self.defaultSetUpTasks()

        import metal_network
        self.module = metal_network

    def test_module_fail_when_required_args_missing(self):
        set_module_args(dict())
        with self.assertRaisesRegexp(AnsibleFailJson,
                                     "{'msg': 'missing required arguments: name, project, partition', 'failed': True}"):
            self.module.main()

    @patch("ansible.module_utils.basic.AnsibleModule.run_command",
           side_effect=[(0, Mock.Metalctl.read("network_ls_01.json"), "")])
    def test_network_present_already_exists(self, mock):
        set_module_args(
            dict(name="test", description="b", partition="fra-equ01", project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f"))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        mock.assert_called()
        mock.assert_called_with(['metalctl', '-o', 'json', 'network', 'ls', '--name', 'test',
                                 '--partition', 'fra-equ01',
                                 '--project', '12e1b1db-44d7-4f57-9c9d-5799b582ab8f'], check_rc=True,
                                environ_update=dict())

        expected = dict(
            id="02cc0b42-f675-4c7d-a671-f7a9c8214b61",
            prefixes=['10.0.156.0/22'],
            changed=False,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("ansible.module_utils.basic.AnsibleModule.run_command",
           side_effect=[(0, "{}", ""), (0, '{"id":"a-uuid", "prefixes": ["10.0.0.0/22"]}', "")])
    def test_network_present_allocated(self, mock):
        set_module_args(dict(name="test2", description="b", partition="fra-equ01", project="a-uuid"))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        calls = [
            call(['metalctl', '-o', 'json', 'network', 'ls', '--name', 'test2', '--partition', 'fra-equ01',
                  '--project', 'a-uuid'],
                 check_rc=True, environ_update=dict()),
            call(['metalctl', '-o', 'json', 'network', 'allocate', '--name', 'test2', '--description', 'b',
                  '--project', 'a-uuid', '--partition', 'fra-equ01'],
                 check_rc=True, environ_update=dict()),
        ]
        mock.assert_called()
        mock.assert_has_calls(calls)

        expected = dict(
            id="a-uuid",
            prefixes=["10.0.0.0/22"],
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("ansible.module_utils.basic.AnsibleModule.run_command",
           side_effect=[(0, Mock.Metalctl.read("network_ls_01.json"), ""),
                        (0, '{"id":"02cc0b42-f675-4c7d-a671-f7a9c8214b61", "prefixes": ["10.0.156.0/22"]}', "")])
    def test_network_absent(self, mock):
        set_module_args(
            dict(name="test", description="b", partition="fra-equ01", project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f",
                 state="absent"))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        calls = [
            call(['metalctl', '-o', 'json', 'network', 'ls', '--name', 'test',
                  '--partition', 'fra-equ01',
                  '--project', '12e1b1db-44d7-4f57-9c9d-5799b582ab8f'], check_rc=True, environ_update=dict()),
            call(['metalctl', '-o', 'json', 'network', 'free', '02cc0b42-f675-4c7d-a671-f7a9c8214b61'],
                 check_rc=True, environ_update=dict()),
        ]
        mock.assert_called()
        mock.assert_has_calls(calls)

        expected = dict(
            id="02cc0b42-f675-4c7d-a671-f7a9c8214b61",
            prefixes=["10.0.156.0/22"],
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)
