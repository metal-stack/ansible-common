from ansible.plugins.action import ActionBase

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display

    display = Display()


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        self._supports_check_mode = True

        result = super(ActionModule, self).run(tmp, task_vars)
        result["changed"] = False

        if self._task.args.get('smart', True) and task_vars.get('ansible_facts', {}).get(
                '_metal_stack_releases_already_executed', False):
            result["skipped"] = True
            return result

        return self._execute_module(module_name="metal_releases", tmp=tmp, task_vars=task_vars)
