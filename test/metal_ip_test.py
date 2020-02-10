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

        import metal_ip
        self.module = metal_ip

    @patch("ansible.module_utils.basic.AnsibleModule.run_command",
           side_effect=[(0, '{"ipaddress": "212.34.89.212"}', "")])
    def test_ip_present_random_ip(self, mock):
        set_module_args(
            dict(name="test", description="b", network="internet-fra-equ01",
                 project="12e1b1db-44d7-4f57-9c9d-5799b582ab8f"))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        mock.assert_called()
        mock.assert_called_with(
            ['metalctl', '-o', 'json', 'network', 'ip', 'allocate', '--project',
             '12e1b1db-44d7-4f57-9c9d-5799b582ab8f', '--network', 'internet-fra-equ01', '--type', 'static', '--name',
             'test', '--description', 'b'], check_rc=True,
            environ_update=dict())

        expected = dict(
            ip="212.34.89.212",
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("ansible.module_utils.basic.AnsibleModule.run_command",
           side_effect=[(0, Mock.Metalctl.read("network_ip_ls_01.json"), "")])
    def test_ip_present_static_ip_already_exists(self, mock):
        set_module_args(
            dict(name="shoot-ip-1", ip="212.34.89.212", description="b", network="internet-fra-equ01",
                 project="2ada3f21-67fc-4432-a9ba-89b670245456"))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        mock.assert_called()
        mock.assert_called_with(
            ['metalctl', '-o', 'json', 'network', 'ip', 'ls', '--ipaddress', '212.34.89.212'], check_rc=True,
            environ_update=dict())

        expected = dict(
            ip="212.34.89.212",
            changed=False,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("ansible.module_utils.basic.AnsibleModule.run_command",
           side_effect=[(0, "{}", ""), (0, '{"ipaddress": "212.34.89.212"}', "")])
    def test_ip_present_static_ip_allocate(self, mock):
        set_module_args(
            dict(name="shoot-ip-1", ip="212.34.89.212", description="b", network="internet-fra-equ01",
                 project="2ada3f21-67fc-4432-a9ba-89b670245456"))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        calls = [
            call(['metalctl', '-o', 'json', 'network', 'ip', 'ls', '--ipaddress', '212.34.89.212'], check_rc=True,
                 environ_update=dict()),
            call(['metalctl', '-o', 'json', 'network', 'ip', 'allocate', '--project',
                  '2ada3f21-67fc-4432-a9ba-89b670245456', '--network', 'internet-fra-equ01', '--type', 'static',
                  '--name', 'shoot-ip-1', '--description', 'b', '212.34.89.212'],
                 check_rc=True, environ_update=dict()),
        ]
        mock.assert_called()
        mock.assert_has_calls(calls)

        expected = dict(
            ip="212.34.89.212",
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    @patch("ansible.module_utils.basic.AnsibleModule.run_command",
           side_effect=[(0, Mock.Metalctl.read("network_ip_ls_01.json"), ""),
                        (0, '{"ipaddress": "212.34.89.212"}', "")])
    def test_ip_absent(self, mock):
        set_module_args(
            dict(name="shoot-ip-1", ip="212.34.89.212", description="b", network="internet-fra-equ01",
                 project="2ada3f21-67fc-4432-a9ba-89b670245456", state="absent"))

        with self.assertRaises(AnsibleExitJson) as result:
            self.module.main()

        calls = [
            call(['metalctl', '-o', 'json', 'network', 'ip', 'ls', '--ipaddress', '212.34.89.212'], check_rc=True,
                 environ_update=dict()),
            call(['metalctl', '-o', 'json', 'ip', 'free', '212.34.89.212'],
                 check_rc=True, environ_update=dict()),
        ]
        mock.assert_called()
        mock.assert_has_calls(calls)

        expected = dict(
            ip="212.34.89.212",
            changed=True,
        )
        self.assertDictEqual(result.exception.module_results, expected)

    def test_ip_absent_ip_arg_required(self):
        set_module_args(
            dict(state="absent"))

        with self.assertRaisesRegexp(AnsibleFailJson, "ip is a required argument when state is absent"):
            self.module.main()
