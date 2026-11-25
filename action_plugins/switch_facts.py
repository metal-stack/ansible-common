#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.plugins.action import ActionBase
try:
    # ansible-core >= 2.21
    from ansible.plugins.action import VariableLayer
except ImportError:
    VariableLayer = None


class ActionModule(ActionBase):
    """
    Runs the switch_facts module on the remote host and registers the
    gathered information as plain host variables instead of facts.
    """

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        self._supports_check_mode = True

        module_result = self._execute_module(
            module_name='switch_facts',
            module_args=self._task.args,
            task_vars=task_vars,
        )
        result.update(module_result)

        if result.get("failed"):
            return result

        return self._register_vars(result, result.get("ansible_facts", {}))

    def _register_vars(self, result, variables):
        """
        Registers the given variables as plain host variables (like set_fact does).

        Returning them only through ansible_facts makes ansible-core inject them as
        top-level facts, which is deprecated (INJECT_FACTS_AS_VARS) and will be removed.
        """
        if VariableLayer is not None:
            # disable legacy behavior of registering 'ansible_facts' from result dict
            self.register_host_variables({}, VariableLayer.CACHEABLE_FACT)
            self.register_host_variables(variables, VariableLayer.EPHEMERAL_FACT)
        # still contained in the result for older ansible versions and for output
        result["ansible_facts"] = variables
        return result
