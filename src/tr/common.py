from tr.logTools import start_raw_logging, stop_raw_logging, verbose
import sys
import re
import os
import traceback
import json
import copy
import yaml
from typing import Any
from pydantic import ValidationError
from enum import Enum

TASK_YES_TOKEN = 'yes'
TASK_NO_TOKEN = 'no'


class TaskException(Exception):
    def __init__(self, error: str) -> None:
        self.error = error

    def __str__(self) -> str:
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


def dict_value(d: dict, path: str, require=False, default=None) -> Any:
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


_const_vars_map: dict = {}
_global_vars_map: dict = {}
_default_vars_map: dict = {}


def set_const_vars_map(vars_map: dict) -> None:
    global _const_vars_map
    global _default_vars_map
    _const_vars_map = vars_map
    _default_vars_map = vars_map


def set_global_vars_map(vars_map: dict) -> None:
    global _global_vars_map
    global _default_vars_map
    _global_vars_map = vars_map
    _default_vars_map = copy.deepcopy(vars_map)
    _default_vars_map.update(_const_vars_map)


def dump_vars(vars_map: dict) -> None:
    start_raw_logging()
    for k, v in vars_map.items():
        verbose("{}='{}'", k, v)
    stop_raw_logging()


def dump_default_vars() -> None:
    dump_vars(_default_vars_map)


class StringVarExpander:
    var_re = re.compile(r'{{\S*?}}')

    def __init__(self, vars_map: dict | None = None) -> None:
        if not vars_map:
            self.vars_map = _default_vars_map
        else:
            self.vars_map = copy.deepcopy(_global_vars_map)
            self.vars_map.update(vars_map)
            self.vars_map.update(_const_vars_map)

        self.expansion_stack = []

    def __call__(self, s: str) -> str:
        if self.expansion_stack:
            raise TaskException("Incomplete variable expansion?")
        return re.sub(StringVarExpander.var_re, self._expand_re, s)

    def _expand_re(self, match) -> str:
        var = match.group()[2:-2]
        if var in self.expansion_stack:
            raise TaskException(f"Recursive expanded var '{var}'")
        if var.startswith("$"):
            return os.getenv(var[1:], "")
        value = self.vars_map.get(var, "")
        if type(value) is list or type(value) is dict:
            raise TaskException(f"Var expanded path '{var}' doesn't refer to valid type")
        self.expansion_stack.append(var)
        s = re.sub(StringVarExpander.var_re, self._expand_re, str(value))
        self.expansion_stack.pop()
        return s


def parse_assignment_str(s: str) -> tuple[str, str]:
    parts = s.split('=', maxsplit=1)
    if len(parts) == 1:
        return s, ""
    return parts[0], parts[1]


def bt() -> None:
    traceback.print_stack(file=sys.stdout)


def print_dict(d: dict) -> None:
    print(json.dumps(d, indent=4))


def sort_dict(item: dict):
    return {k: sort_dict(v) if isinstance(v, dict) else v for k, v in sorted(item.items())}


class DictDumpFmt(str, Enum):
    JSON = "json"
    YAML = "yaml"


def dump_dict(d: dict, sort: bool, fmt: str) -> str:
    if sort:
        d = sort_dict(d)

    if fmt == DictDumpFmt.YAML:
        return yaml.dump(d, sort_keys=False)
    else:
        return json.dumps(d, indent=4)


def pydantic_errmsg(ve: ValidationError) -> str:
    errs = []
    for e in ve.errors():
        try:
            loc_len = len(e["loc"])
            if loc_len == 0:
                loc = "<ROOT>"
            elif loc_len == 1 and isinstance(e["loc"][0], int):
                token = e["loc"][0]
                loc = f"index {token}"
            else:
                loc = "/".join(str(i) for i in e["loc"])
            errs.append(f"'{loc}': {e['msg']}")
        except Exception:
            errs.append(str(e))
    return "\n".join(errs)
