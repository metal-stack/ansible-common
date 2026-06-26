#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display

    display = Display()

from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from ansible import constants as C

# Mapping of type parameter values to (color_constant, prefix_string).
# Colors match those defined in ansible.utils.display.Display and are the
# same ones Ansible uses internally for its own output.
_MESSAGE_TYPES = {
    "deprecate": (C.COLOR_DEPRECATE, "[DEPRECATED]"),
    "info": (C.COLOR_OK, "[INFO]"),
    "warning": (C.COLOR_WARN, "[WARNING]"),
    "error": (C.COLOR_ERROR, "[ERROR]"),
    "debug": (C.COLOR_DEBUG, "[DEBUG]"),
    "verbose": (C.COLOR_VERBOSE, "[VERBOSE]"),
    "changed": (C.COLOR_CHANGED, "[CHANGED]"),
    "skip": (C.COLOR_SKIP, "[SKIP]"),
    "unreachable": (C.COLOR_UNREACHABLE, "[UNREACHABLE]"),
    "ok": (C.COLOR_OK, "[OK]"),
    "included": (C.COLOR_INCLUDED, "[INCLUDED]"),
}

_DEFAULT_TYPE = "info"


class ActionModule(ActionBase):
    """Action plugin that prints a formatted message via the Ansible display mechanism.

    Supports multiple message types (deprecate, info, warning, error, etc.),
    each rendered in the colour Ansible uses natively for that severity.

    An optional ``action`` line is emitted on its own line so that URLs are
    never broken mid-word by line-wrapping.

    Runs entirely on the controller — no remote execution needed.
    """

    # Skips the setup Ansible would otherwise do to copy files to the remote host.
    TRANSFERS_FILES = False
    # Ansible checks task arguments against this set and warns on unknown keys.
    _VALID_ARGS = frozenset(["msg", "action", "type"])

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = {}

        self._supports_check_mode = True

        result = super(ActionModule, self).run(tmp, task_vars)
        # tmp was a remote temp-directory path, deprecated and always None in modern Ansible.
        # Deleting it is the idiomatic way to signal intentional non-use.
        del tmp

        msg_type = self._task.args.get("type", _DEFAULT_TYPE)
        if msg_type not in _MESSAGE_TYPES:
            supported = ", ".join(sorted(_MESSAGE_TYPES.keys()))
            raise AnsibleError(
                "unknown type '{}'. Supported types: {}".format(msg_type, supported)
            )

        color, prefix = _MESSAGE_TYPES[msg_type]

        msg = self._task.args.get("msg", "This role is deprecated.")
        action = self._task.args.get("action")

        warning = msg.strip()

        # Use display.display() instead of display.warning() to bypass
        # textwrap.wrap() which is called by warning() and which:
        # (a) collapses embedded \n to spaces, and
        # (b) breaks URLs at hyphens (break_on_hyphens=True by default),
        # making them non-clickable in log viewers.
        #
        # Deduplication: callers should add run_once: true to the task so that
        # Ansible itself only executes the task once per play, regardless of
        # how many hosts are in the inventory.  There is no deduplication logic
        # here intentionally — action plugins run in per-host worker processes,
        # which means any in-process counter would only be effective within a
        # single worker anyway.
        display.display(prefix + ": " + warning, color=color, stderr=True)

        if action:
            action_text = action.strip()
            display.display("[ACTION]: " + action_text, color=color, stderr=True)
            warning = "{}\n{}\n".format(warning, action_text)

        result["msg"] = warning
        result["changed"] = False
        result["failed"] = False
        return result
