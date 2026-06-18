#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display

    display = Display()

from ansible.plugins.action import ActionBase
from ansible import constants as C

class ActionModule(ActionBase):
    """Action plugin that emits a deprecation warning for a role.

    Runs entirely on the controller — no remote execution needed.
    """

    # Skips the setup Ansible would otherwise do to copy files to the remote host.
    TRANSFERS_FILES = False
    # Ansible checks task arguments against this set and warns on unknown keys.
    _VALID_ARGS = frozenset(["msg", "alternative"])

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = {}

        self._supports_check_mode = True

        result = super(ActionModule, self).run(tmp, task_vars)
        # tmp was a remote temp-directory path, deprecated and always None in modern Ansible.
        # Deleting it is the idiomatic way to signal intentional non-use.
        del tmp

        msg = self._task.args.get("msg", "This role is deprecated.")
        alternative = self._task.args.get("alternative")

        warning = msg.strip()

        # Use display.display() instead of display.warning() to bypass
        # textwrap.wrap() which is called by warning() and which:
        # (a) collapses embedded \n to spaces, and
        # (b) breaks URLs at hyphens (break_on_hyphens=True by default),
        # making them non-clickable in log viewers.
        # Using [DEPRECATED] prefix and the deprecation color to distinguish
        # this from generic warnings.
        #
        # Deduplication: callers should add run_once: true to the task so that
        # Ansible itself only executes the task once per play, regardless of
        # how many hosts are in the inventory.  There is no deduplication logic
        # here intentionally — action plugins run in per-host worker processes,
        # which means any in-process counter would only be effective within a
        # single worker anyway.
        display.display("[DEPRECATED]: " + warning, color=C.COLOR_DEPRECATE, stderr=True)

        if alternative:
            alt_text = alternative.strip()
            display.display("[ALTERNATIVE]: " + alt_text, color=C.COLOR_DEPRECATE, stderr=True)
            warning = "{}\n{}\n".format(warning, alt_text)

        result["msg"] = warning
        result["changed"] = False
        result["failed"] = False
        return result
