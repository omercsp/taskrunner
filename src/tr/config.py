from tr.common import (TaskException, StringVarExpander, set_const_vars_map, set_global_vars_map,
                       dump_default_vars, pydantic_errmsg)
from tr.logTools import info, verbose, logging_enabled_for
import logging
import os
import pathlib
import json
from typing import Any
from argparse import Namespace as Args
from pydantic import BaseModel, Field, ConfigDict, ValidationError, AliasChoices
from copy import deepcopy
import yaml
from enum import Enum
from functools import cache


_COMMON_CONF_FILES: list[str] = [".tasks.yaml", "tasks.yaml", ".tasks.json", "tasks.json"]
_DFLT_CONF_DIR = str(pathlib.Path.home()) + "/.config/"
_DFLT_CONF_FILES = [os.path.join(_DFLT_CONF_DIR, f) for f in _COMMON_CONF_FILES]


@cache
def _find_default_config_file(directory: str) -> str | None:
    for f in _COMMON_CONF_FILES:
        file_path = os.path.join(directory, f)
        if os.path.isfile(file_path):
            return file_path
    return None


HIDDEN = "hidden"
ABSTRACT = "abstract"
INCLUDE = "include"
TASKS = "tasks"
VARIABLES = "variables"
COMMANDS = "commands"
ENV = "env"
C_VOLUMES = "c_volumes"
C_ENV = "c_env"


class _CmdsInherit(str, Enum):
    Ignore = "ignore"
    Default = "default"
    Before = "before"
    After = "after"


class TaskModel(BaseModel):
    model_config = ConfigDict(extra='forbid')
    base: str | None = None
    base_cmds: _CmdsInherit = Field(_CmdsInherit.Default,
                                    validation_alias=AliasChoices("base_cmds", "base_commands"))
    short_desc: str | None = Field(None, max_length=75,
                                   validation_alias=AliasChoices("short_desc", "short_description"))
    long_desc: str | None = Field(None, validation_alias=AliasChoices("long_desc", "description"))
    commands: list[str] = Field(default_factory=list)
    cwd: str | None = None
    shell: bool = False
    shell_path: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    inherit_os_env: bool = True
    inherit_env: bool = True
    stop_on_error: bool = True
    hidden: bool = False
    abstract: bool = False
    variables: dict[str, str] = Field(default_factory=dict)
    inherit_variables: bool = True
    #  Container related
    c_image: str | None = None
    c_container_tool: str | None = None
    c_volumes: list[str] = Field(default_factory=list)
    c_inherit_volumes: bool = True
    c_interactive: bool = False
    c_tty: bool = False
    c_flags: str | None = None
    c_exec: bool = False
    c_remove: bool = True
    c_sudo: bool = False
    c_shell: bool = False
    c_shell_path: str | None = None
    c_env: dict[str, str] = Field(default_factory=dict)
    c_inherit_env: bool = True
    c_cwd: str | None = None


class ConfigFileModel(BaseModel):
    model_config = ConfigDict(extra='forbid')
    json_schema: str | None = Field(None, alias="$schema")
    includes: list[str] = Field(default_factory=list, alias=INCLUDE)
    use_default_include: bool = True
    tasks: dict[str, Any] = Field(default_factory=dict)
    suppress: list[str] = Field(default_factory=list)
    variables: dict[str, str] = Field(default_factory=dict)
    default_task: str | None = None
    default_shell_path: str = Field("/bin/sh", max_length=255)
    default_container_tool: str = Field("/usr/bin/docker", max_length=255)
    default_container_shell_path: str = Field("/bin/sh", max_length=255)


def validate_config_file_schema(data: dict) -> ConfigFileModel:
    try:
        return ConfigFileModel(**data)
    except ValidationError as e:
        s = pydantic_errmsg(e)
        raise TaskException(f"Schema validation error: {s}")


def validate_task_model(name: str, data: dict) -> TaskModel:
    try:
        return TaskModel(**data)
    except ValidationError as e:
        s = pydantic_errmsg(e)
        raise TaskException(f"Task schema validation error for '{name}:'\n{s}")


class Config:
    @staticmethod
    def _read_config_file(file_path: str) -> ConfigFileModel:
        #  Find the configuration file extension
        try:
            ext = os.path.splitext(file_path)[1]
            if ext == ".json":
                data: dict = json.load(open(file_path, 'r'))
            elif ext == ".yaml" or ext == ".yml":
                data: dict = yaml.safe_load(open(file_path, 'r')) or {}
            else:
                raise TaskException("Unsupported configuration file format")
            return validate_config_file_schema(data)
        except (IOError, TypeError, ValueError, TaskException, IndexError, yaml.YAMLError) as e:
            raise TaskException(f"Error parsing {file_path} - {e}")

    def _read_configuration(self, file_path: str, read_files: set | None = None) -> ConfigFileModel:
        if read_files is None:
            read_files = set()
        includes = []
        base_config_model = None
        info("Reading configuration file {}", file_path)
        base_config_model = Config._read_config_file(file_path)
        includes = base_config_model.includes

        # Add the default configuration file to includes list but only for the original
        # configuration file, and the behavior isn't turned off (again, relevant ONLY to
        # original file)
        dflt_conf_file_path = _find_default_config_file(_DFLT_CONF_DIR)
        if len(read_files) == 0 and \
                file_path not in _DFLT_CONF_FILES and \
                dflt_conf_file_path and \
                base_config_model.use_default_include and \
                dflt_conf_file_path not in includes:
            includes.insert(0, dflt_conf_file_path)

        included_tasks = {}
        included_variables = {}
        info(f"Configuration file includes: {includes}")
        read_files.add(file_path)
        expander = StringVarExpander()
        for f in includes:
            f = expander(f)
            if f in read_files:
                raise TaskException(f"Include loop detected - '{f}'")
            included_model = self._read_configuration(f, read_files)
            included_tasks.update(included_model.tasks)
            included_variables.update(included_model.variables)
        included_tasks.update(base_config_model.tasks)
        included_variables.update(base_config_model.variables)

        base_config_model.tasks = included_tasks
        base_config_model.variables = included_variables
        return base_config_model

    @staticmethod
    def _get_conf_file_path() -> str | None:
        directory = os.getcwd()
        while True:
            conf_path = _find_default_config_file(directory)
            if conf_path:
                return conf_path
            if directory == "/":
                break
            directory = os.path.dirname(directory)

        return _find_default_config_file(_DFLT_CONF_DIR)

    def __init__(self, args: Args | None) -> None:
        self.args: Args = args  # type: ignore
        if args and args.conf:
            conf_path = args.conf
        else:
            conf_path = Config._get_conf_file_path()

        if not conf_path:
            raise TaskException("No task configuration file found")

        #  Populate some variables early so they are available for the rest of the configuration
        const_vars = {}
        cwd = os.getcwd()
        const_vars[AutoVarsKeys.CWD] = cwd
        conf_dir_name = os.path.dirname(conf_path)
        if conf_dir_name and conf_path != _find_default_config_file(_DFLT_CONF_DIR):
            const_vars[AutoVarsKeys.TASK_ROOT] = os.path.dirname(conf_path)
        else:
            const_vars.setdefault(AutoVarsKeys.TASK_ROOT, cwd)
        if args and args.__contains__(AutoVarsKeys.TASK_CLI_ARGS):
            const_vars[AutoVarsKeys.TASK_CLI_ARGS] = " ".join(
                args.__getattribute__(AutoVarsKeys.TASK_CLI_ARGS))
        set_const_vars_map(const_vars)

        self.conf = self._read_configuration(conf_path)

        set_global_vars_map(self.conf.variables)

        if logging_enabled_for(logging.DEBUG):
            dump_default_vars()

    @property
    def tasks(self) -> dict:
        return self.conf.tasks

    def default_task_name(self) -> str | None:
        return self.conf.default_task

    @property
    def default_container_tool(self) -> str:
        return self.conf.default_container_tool

    @property
    def default_container_shell_path(self) -> str:
        return self.conf.default_container_shell_path

    @property
    def default_shell_path(self) -> str:
        return self.conf.default_shell_path

    def visible_tasks(self) -> list[str]:
        tasks = set()
        for name, task in self.tasks.items():
            if not task.get(HIDDEN, False):
                tasks.add(name)
        return list(tasks)

    def _raw_task_obj(self, name: str) -> dict:
        if name in self.tasks:
            return self.tasks[name]
        tasks = [t for t in self.tasks if t.startswith(name)]
        if len(tasks) == 1:
            return self.tasks[tasks[0]]
        if len(tasks) > 1:
            raise TaskException(f"Ambiguous task name '{name}'")
        raise TaskException(f"No such task '{name}'")

    def task_desc(self, name: str, included_list: set | None) -> dict:

        if included_list is not None:
            if name in included_list:
                raise TaskException(f"Inheritance loop detected for task '{name}'")
            included_list.add(name)

        task_desc = self._raw_task_obj(name)
        task_model = validate_task_model(name, task_desc)
        base_task_name = task_model.base
        if included_list is None or base_task_name is None or not base_task_name.strip():
            return task_desc

        base_task_desc = self.task_desc(base_task_name, included_list)
        base_task_desc = deepcopy(base_task_desc)
        base_task_desc.pop(HIDDEN, None)
        base_task_desc.pop(INCLUDE, None)
        base_task_desc.pop(ABSTRACT, None)

        tmp_vars = {}
        if task_model.inherit_variables:
            tmp_vars.update(base_task_desc.get(VARIABLES, {}))
        tmp_vars.update(task_model.variables)

        tmp_env = {}
        if task_model.inherit_env:
            tmp_env.update(base_task_desc.get(ENV, {}))
        tmp_env.update(task_model.env)

        tmp_c_env = {}
        if task_model.c_inherit_env:
            tmp_c_env.update(base_task_desc.get(C_ENV, {}))
        tmp_c_env.update(task_model.c_env)

        tmp_volumes = task_model.c_volumes
        if task_model.c_inherit_volumes:
            task_model.c_volumes += base_task_desc.get(C_VOLUMES, [])

        base_commands = base_task_desc.pop(COMMANDS, [])
        commands = []
        if not task_model.commands:
            if task_model.base_cmds == _CmdsInherit.Default:
                commands = base_commands
            elif task_model.base_cmds != _CmdsInherit.Ignore:
                commands = task_model.commands
        elif base_commands:
            if task_model.base_cmds == _CmdsInherit.Before:
                commands = base_commands + task_model.commands
            elif task_model.base_cmds == _CmdsInherit.After:
                commands = task_model.commands + base_commands
            else:
                commands = task_model.commands

        unified_desc = {}
        unified_desc.update(base_task_desc)
        unified_desc.update(task_desc)
        unified_desc[COMMANDS] = commands
        unified_desc[VARIABLES] = tmp_vars
        unified_desc[ENV] = tmp_env
        unified_desc[C_ENV] = tmp_c_env
        unified_desc[C_VOLUMES] = tmp_volumes
        return unified_desc

    def task_model(self, name: str, includes: bool) -> TaskModel:
        verbose("Task '{}' requested, with_inclusions={}", name, includes)
        if includes:
            desc = self.task_desc(name, set())
        else:
            desc = self.task_desc(name, None)
        return validate_task_model(name, desc)


class AutoVarsKeys(object):
    TASK_ROOT = "taskRoot"
    CWD = "cwd"
    TASK_CLI_ARGS = "cliArgs"
