import logging
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
            raise TaskException("No '{}' setting was found".format(path))
    return default


def init_logging():
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                        format='%(filename)s:%(lineno)d %(levelname)s - %(message)s')


class StringVarExpander(object):
    var_re = re.compile(r'{{\S*?}}')

    def __init__(self, defs: dict, previous_expansions: set = None):
        self.previous_expansions = set() if previous_expansions is None else previous_expansions
        self.defs = defs

    def expand(self, s: str) -> str:
        return re.sub(StringVarExpander.var_re, self._expand_re, s)

    def _expand_re(self, match) -> str:
        var = match.group()[2:-2]
        if var in self.previous_expansions:
            raise TaskException("Recursive expanded var '{}'".format(var))
        if var.startswith("$"):
            return os.getenv(var[1:], "")
        value = self.defs.get(var, "")
        if type(value) is list or type(value) is dict:
            raise TaskException("Var expanded path '{}' doesn't refer to valid type".format(var))
        self.previous_expansions.add(var)
        next_expander = StringVarExpander(self.defs, self.previous_expansions)
        return re.sub(StringVarExpander.var_re, next_expander._expand_re, str(value))


def expand_string(s: str, defs: dict):
    return StringVarExpander(defs, set()).expand(s)


def parse_assignmet_str(s: str):
    parts = s.split('=', maxsplit=1)
    if len(parts) == 1:
        return s, ""
    return parts[0], parts[1]


def bt():
    traceback.print_stack(file=sys.stdout)


def print_dict(d: dict):
    print(json.dumps(d, indent=4))
