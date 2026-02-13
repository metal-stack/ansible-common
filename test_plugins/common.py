from __future__ import annotations


def is_list(value):
    return isinstance(value, list)


class TestModule(object):
    def tests(self):
        return {
            'is_list': is_list,
        }
