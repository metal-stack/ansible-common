#!/usr/bin/python
# -*- coding: utf-8 -*-

from traceback import format_exc
from yaml import safe_load

from ansible.module_utils.urls import open_url
from ansible.plugins.action import ActionBase
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.module_utils._text import to_native

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display

    display = Display()


class ActionModule(ActionBase):
    def _ensure_invocation(self, result):
        # NOTE: adding invocation arguments here needs to be kept in sync with
        # any no_log specified in the argument_spec in the module.
        # This is not automatic.
        if 'invocation' not in result:
            if self._play_context.no_log:
                result['invocation'] = "CENSORED: no_log is set"
            else:
                # NOTE: Should be removed in the future. For now keep this broken
                # behaviour, have a look in the PR 51582
                result['invocation'] = self._task.args.copy()
                result['invocation']['module_args'] = self._task.args.copy()

        return result

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        self._supports_check_mode = True

        version = self._task.args.get('version', None)
        image_vector_url_template = self._task.args.get('image_vector_url_template',
                                                        "https://raw.githubusercontent.com/metal-stack/releases/%s/release.yaml")
        image_vector_mapping = self._task.args.get('mapping')
        smart = boolean(self._task.args.get('smart', True), strict=False)

        result["changed"] = False
        result['failed'] = True
        if not version:
            result['msg'] = 'version is required'
        elif not image_vector_mapping:
            result['msg'] = 'image_vector_mapping is required'
        else:
            del result['failed']

        if result.get('failed'):
            return self._ensure_invocation(result)

        if smart and task_vars.get('ansible_facts', {}).get('_metal_stack_releases_already_executed', False):
            result["skipped"] = True
            return self._ensure_invocation(result)

        url = image_vector_url_template % version
        try:
            rsp = open_url(url)
            image_vector = safe_load(rsp.read())
        except Exception as e:
            result["failed"] = True
            result["msg"] = "error getting image vector from url: %s" % url
            result["error"] = to_native(e)
            result["traceback"] = format_exc()
            return self._ensure_invocation(result)

        ansible_facts = dict()
        for k, path in image_vector_mapping.items():
            if task_vars.get(k) is not None:
                continue

            value = image_vector
            for p in path.split("."):
                try:
                    value = value[p]
                except KeyError as e:
                    result["failed"] = True
                    result["msg"] = "error reading image versions from release vector, %s not found in path: %s" % (
                        to_native(e), path)
                    return self._ensure_invocation(result)

            ansible_facts[k] = value

        ansible_facts["_metal_stack_releases_already_executed"] = True
        result["ansible_facts"] = ansible_facts

        return self._ensure_invocation(result)
