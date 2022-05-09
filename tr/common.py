from tr.logTools import *
import sys
import re
import typing
import os
import traceback
import json

TASK_YES_TOKEN = 'yes'
TASK_NO_TOKEN = 'no'


class TaskException(Exception):
    def __init__(self, error):
        self.error = error

    def __str__(self):
        return self.error


def _dict_path_elements(path: str) -> list:
    elements = []
    for element in path.split('/'):
        if element.startswith("#"):
            try:
                index_el = int(element[1:])
                element = index_el
            except (IndexError, ValueError):
                pass
        elements.append(element)
    return elements


def dict_value(d: dict, path: str, require=False, default=None) -> typing.Any:
    elements = _dict_path_elements(path)
    field = d
    try:
        for element in elements:
            field = field[element]
        return field

    except (KeyError, IndexError):
        if require:
            raise TaskException(f"No '{path}' setting was found")
    return default


class StringVarExpander(object):
    var_re = re.compile(r'{{\S*?}}')

    def __init__(self):
        self.curr_expansion_stack = []
        self.map = {}

    def __call__(self, s: str) -> str:
        self.curr_expansion_stack = []
        return re.sub(StringVarExpander.var_re, self._expand_re, s)

    def _expand_re(self, match) -> str:
        var = match.group()[2:-2]
        if var in self.curr_expansion_stack:
            raise TaskException(f"Recursive expanded var '{var}'")
        if var.startswith("$"):
            return os.getenv(var[1:], "")
        value = self.map.get(var, "")
        if type(value) is list or type(value) is dict:
            raise TaskException(f"Var expanded path '{var}' doesn't refer to valid type")
        self.curr_expansion_stack.append(var)
        s = re.sub(StringVarExpander.var_re, self._expand_re, str(value))
        self.curr_expansion_stack.pop()
        return s


def parse_assignment_str(s: str):
    parts = s.split('=', maxsplit=1)
    if len(parts) == 1:
        return s, ""
    return parts[0], parts[1]


def bt():
    traceback.print_stack(file=sys.stdout)


def print_dict(d: dict):
    print(json.dumps(d, indent=4))
