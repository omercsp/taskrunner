import logging
import sys
import re
import typing
import os


class TaskException(Exception):
    def __init__(self, error):
        self.error = error

    def __str__(self):
        return self.error


def _json_dict_path_elements(path: str) -> list:
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


def json_dict_value(d: dict, path: str, require=False, default=None, val_type=str) -> typing.Any:
    elements = _json_dict_path_elements(path)
    field = d
    try:
        for element in elements:
            field = field[element]
        if val_type is not None and type(field) is not val_type:
            raise TaskException("Value type of '{}' isn't a {}".format(path, val_type))
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

    def __init__(self, defs: dict, previous_expansions: list):
        self.previous_expansions = previous_expansions
        self.defs = defs

    def expand(self, s: str) -> str:
        return re.sub(StringVarExpander.var_re, self._expand_re, s)

    def _expand_re(self, match) -> str:
        var = match.group()[2:-2]
        if var in self.previous_expansions:
            raise TaskException("Recursive expanded var '{}'".format(var))
        if var.startswith("$"):
            if len(var) == 1:
                raise TaskException("Empty environment variable definition")
            var = var[1:]
            return os.getenv(var, "")
        value = self.defs.get(var, "")
        if type(value) is list or type(value) is dict:
            raise TaskException("Var expanded path '{}' doesn't refer to valid type".format(var))
        next_expander = StringVarExpander(self.defs, self.previous_expansions + [var])
        return re.sub(StringVarExpander.var_re, next_expander._expand_re, str(value))


def expand_string(s: str, defs: dict):
    return StringVarExpander(defs, []).expand(s)
