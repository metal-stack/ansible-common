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
    ALREADY_RESOLVED_MARKER = "_yaml_files_already_resolved"

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

        files = self._task.args.get('files', task_vars.get('setup_yaml'))
        smart = boolean(self._task.args.get('smart', task_vars.get('setup_yaml_smart', True)), strict=False)
        if not files:
            result["skipped"] = True
            return result

        result["failed"] = True
        if not isinstance(files, list):
            result["msg"] = "files must be a list"
        else:
            del result["failed"]

        if result.get("failed"):
            return result

        if smart and task_vars.get("ansible_facts", {}).get(self.ALREADY_RESOLVED_MARKER, False):
            result["skipped"] = True
            return self._ensure_invocation(result)

        result["changed"] = False

        for f in files:
            version = f.get('version')
            recursive = f.get('recursive', True)
            info = f.get('info')
            info_var = f.get('var')
            if not info and info_var:
                info = task_vars.get(info_var)

            url_template = info.get("url_template")
            mapping = info.get("mapping")
            nested = info.get("nested", list()) if recursive else list()

            result["failed"] = True
            if not version:
                result["msg"] = "version is required in a file"
            elif not info:
                result["msg"] = "info is required in a file"
            elif not url_template:
                result["msg"] = "url_template is required in a file"
            elif not mapping:
                result["msg"] = "mapping is required in a file"
            else:
                del result["failed"]

            if result.get("failed"):
                return result

            result = self.resolve(url_template, version, mapping, nested, task_vars, result)
            if result.get("failed"):
                return result

        return self._ensure_invocation(result)

    def resolve(self, url_template, version, mapping, nested, task_vars, result):
        result["failed"] = True
        if not version:
            result["msg"] = "version is required"
        elif not url_template:
            result["msg"] = "url_template is required"
        elif not mapping:
            result["msg"] = "mapping is required"
        else:
            del result["failed"]

        if result.get("failed"):
            return result

        url = url_template % version
        try:
            rsp = open_url(url)
            f = safe_load(rsp.read())
        except Exception as e:
            result["failed"] = True
            result["msg"] = "error getting image vector from url: %s" % url
            result["error"] = to_native(e)
            result["traceback"] = format_exc()
            return result

        for n in nested:
            url_template_path = n.get("url_template_path")
            version_path = n.get("version_path")
            mapping_var = n.get("mapping_var")
            next_nested = n.get("nested", [])

            result["failed"] = True
            if not url_template_path:
                result["msg"] = "url_template_path is required in nested"
            elif not version_path:
                result["msg"] = "version_path is required in nested"
            elif not mapping_var:
                result["msg"] = "mapping_var is required in nested"
            else:
                del result["failed"]

            if result.get("failed"):
                return result

            try:
                u = self.resolve_path(f, url_template_path)
                v = self.resolve_path(f, version_path)
                m = self.resolve_path(task_vars, mapping_var)
            except KeyError as e:
                result["failed"] = True
                result["msg"] = "error resolving path: %s" % url_template_path
                result["error"] = to_native(e)
                result["traceback"] = format_exc()
                return result

            result = self.resolve(u, v, m, next_nested, task_vars, result)
            if result.get("failed"):
                return result

        ansible_facts = dict()
        for k, path in mapping.items():
            if task_vars.get(k) is not None:
                # skip when already defined
                continue

            try:
                value = self.resolve_path(f, path)
            except KeyError as e:
                display.warning(
                    """error reading variable from file, variable %s not found in path: %s 
                    
                    (does the mapping match the version ('%s') of the YAML file?)""" % (
                        to_native(e), path, version))
                continue

            ansible_facts[k] = value

        result["ansible_facts"] = result.get("ansible_facts", {self.ALREADY_RESOLVED_MARKER: True})
        result["ansible_facts"].update(ansible_facts)
        return result

    @staticmethod
    def resolve_path(vector, path):
        value = vector
        for p in path.split("."):
            value = value[p]
        return value
