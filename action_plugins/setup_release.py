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
    ALREADY_RESOLVED_MARKER = "_releases_already_resolved"

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

        releases = self._task.args.get('releases', task_vars.get('setup_release'))
        smart = boolean(self._task.args.get('smart', task_vars.get('setup_release_smart', True)), strict=False)
        if not releases:
            result["skipped"] = True
            return result

        result["failed"] = True
        if not isinstance(releases, list):
            result["msg"] = "releases must be a list"
        else:
            del result["failed"]

        if result.get("failed"):
            return result

        if smart and task_vars.get("ansible_facts", {}).get(self.ALREADY_RESOLVED_MARKER, False):
            result["skipped"] = True
            return self._ensure_invocation(result)

        result["changed"] = False

        for release in releases:
            version = release.get('version')
            name = release.get('name', '')
            recursive = release.get('recursive', True)

            release_key = self.release_name_to_var(name) + "_release"
            release_info = task_vars.get(release_key, dict())
            release_url_template = release_info.get("url_template")
            release_mapping = release_info.get("mapping")
            release_nested = release_info.get("nested", list()) if recursive else list()

            result["failed"] = True
            if not version:
                result["msg"] = "version is required in a release"
            elif not name:
                result["msg"] = "name is required in a release"
            elif not release_info:
                result["msg"] = "release info variable %s is not defined" % release_key
            elif not release_url_template:
                result["msg"] = "url_template is required in a release"
            elif not release_mapping:
                result["msg"] = "mapping is required in a release"
            else:
                del result["failed"]

            if result.get("failed"):
                return result

            result = self.resolve(release_url_template, version, release_mapping, release_nested, task_vars, result)
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
            image_vector = safe_load(rsp.read())
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
                u = self.resolve_path(image_vector, url_template_path)
                v = self.resolve_path(image_vector, version_path)
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
                value = self.resolve_path(image_vector, path)
            except KeyError as e:
                display.warning(
                    """error reading image version from release vector, %s not found in path: %s 
                    
                    (does the mapping match the given release '%s'?)""" % (
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

    @staticmethod
    def release_name_to_var(name):
        return name.lower().replace("-", "_")
