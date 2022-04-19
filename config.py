from schemas import Schema
from common import *
import os
import pathlib
import json


_CONF_FILE_NAME = "tasks.json"
_DFLT_CONF_FILE_NAME = str(pathlib.Path.home()) + "/.config/" + _CONF_FILE_NAME


class Config(object):
    @staticmethod
    def _read_tasks_file(file_path: str) -> dict:
        try:
            data: dict = json.load(open(file_path, 'r'))
        except (IOError, TypeError, ValueError, TaskException) as e:
            raise TaskException("Error parsing {} - {}".format(file_path, e))
        return data

    def _check_config_file_version(self, path: str) -> None:
        major = self.conf[Schema.Keys.Version][Schema.Keys.Ver.Major]
        minor = self.conf[Schema.Keys.Version][Schema.Keys.Ver.Minor]
        if major != Schema.Version.MAJOR or minor > Schema.Version.MINOR:
            raise TaskException(("Incompatible major configuration version for '{}': " +
                                 "Found:{}.{}, expected <= {}.{}").format(
                path, major, minor, Schema.Version.MAJOR, Schema.Version.MINOR))
        if minor != Schema.Version.MINOR:
            print("Incompatible minor configuration version for '{}'".format(str))

    def _read_configuration(self, file_path: str, read_files: set = set()):
        conf = {}
        tasks = {}
        defs = {}
        info("Reading configuration file {}", file_path)
        orig_conf = Config._read_tasks_file(file_path)
        includes = orig_conf.get(Schema.Keys.Include, [])
        if file_path != _DFLT_CONF_FILE_NAME and \
                os.path.isfile(_DFLT_CONF_FILE_NAME) and \
                orig_conf.get(Schema.Keys.UseDfltInclude, True):
            includes.insert(0, _DFLT_CONF_FILE_NAME)

        info("Configuration file includes: {}", includes)
        read_files.add(file_path)
        for f in includes:
            f = self.expander(f)
            if f in read_files:
                raise TaskException("Include loop detected - '{}'".format(f))
            included_conf = self._read_configuration(f, read_files)
            tasks.update(included_conf.get(Schema.Keys.Tasks))
            defs.update(included_conf.get(Schema.Keys.Variables))
            conf.update(included_conf)
        read_files.remove(file_path)
        if Schema.Keys.Include in conf:
            conf.pop(Schema.Keys.Include)

        conf.update(orig_conf)
        tasks.update(orig_conf.get(Schema.Keys.Tasks, {}))
        for supressed_task in conf.get(Schema.Keys.Suppress, []):
            if supressed_task in tasks:
                info("Removing suppressed task {}", supressed_task)
                tasks.pop(supressed_task)
        conf[Schema.Keys.Tasks] = tasks
        defs.update(orig_conf.get(Schema.Keys.Variables, {}))
        conf[Schema.Keys.Variables] = defs
        return conf

    @staticmethod
    def _get_conf_file_path(cli_conf: typing.Union[str, None]) -> typing.Union[str, None]:
        if cli_conf:
            return cli_conf

        directory = os.getcwd()
        while True:
            conf_path = directory + "/." + _CONF_FILE_NAME
            if os.path.isfile(conf_path):
                return conf_path
            if directory == "/":
                break
            directory = os.path.dirname(directory)

        if os.path.isfile(_DFLT_CONF_FILE_NAME):
            return _DFLT_CONF_FILE_NAME
        return None

    def __init__(self, cli_conf: typing.Union[str, None], cli_defs: list, cli_args: typing.List[str]):
        self.expander = StringVarExpander()
        conf_path = Config._get_conf_file_path(cli_conf)

        #  Populate some variables early so they are available in
        early_vars = {}
        cwd = os.getcwd()
        early_vars[Schema.Keys.AutoVars.CWD] = cwd
        if conf_path:
            early_vars[Schema.Keys.AutoVars.TASK_ROOT] = os.path.dirname(conf_path)
        else:
            early_vars[Schema.Keys.AutoVars.TASK_ROOT] = cwd

        self.conf = {}
        if conf_path:
            self.expander.map = early_vars
            self.conf = self._read_configuration(conf_path)
            Schema.validate(self.conf)
            self._check_config_file_version(conf_path)

        #  Always override configuration variables with hard coded ones
        self.vars = self.conf.get(Schema.Keys.Variables, {})
        self.vars.update(early_vars)
        self.tasks = self.conf.get(Schema.Keys.Tasks, {})
        self.vars[Schema.Keys.AutoVars.CLI_ARGS] = " ".join(cli_args)
        if cli_defs:
            for d in cli_defs:
                key, val = parse_assignment_str(d)
                self.vars[key] = val
        self.expander.map = self.vars
        if logging_enabled_for(logging.DEBUG):
            verbose("Unexapnded variables:")
            start_raw_logging()
            for k, v in self.vars.items():
                verbose("{}='{}'", k, v)
            stop_raw_logging()

    def default_task_name(self) -> typing.Union[str, None]:
        return self.setting(Schema.Keys.DfltTask)

    def default_container_tool(self) -> str:
        return self.setting(Schema.Keys.DfltContainerTool, default="/usr/bin/docker")

    def default_container_shell_path(self) -> str:
        return self.setting(Schema.Keys.DfltContainerShellPath, default="/usr/bin/sh")

    def default_shell_path(self) -> typing.Union[str, None]:
        return self.setting(Schema.Keys.DfltShellPath, None)

    def visible_tasks(self) -> typing.List[str]:
        tasks = set()
        for name, task in self.tasks.items():
            if not task.get(Schema.Keys.Task.Hidden, False):
                tasks.add(name)
        return list(tasks)

    #  Return anything. Types is forced by schema validations.
    def setting(self, path: str, default=None) -> typing.Any:
        return dict_value(self.conf, path, default=default)

    def _raw_task_obj(self, name: str) -> dict:
        try:
            return self.tasks[name]
        except KeyError:
            raise TaskException("No such task '{}'".format(name))

    def _task_desc(self, name, included_list: set):
        if name in included_list:
            raise TaskException("Include loop detected for '{}'".format(name))

        base_task = self._raw_task_obj(name)
        hidden = base_task.get(Schema.Keys.Task.Hidden, False)

        included_task = base_task.get(Schema.Keys.Task.Base, None)
        if included_task is None:
            return base_task

        # We about to modify the included object, so deep copy it
        included_task = self._task_desc(
            included_task, included_list=included_list).copy()
        included_task.update(base_task)
        included_task[Schema.Keys.Task.Hidden] = hidden
        return included_task

    def get_task_desc(self, name: str, includes: bool):
        verbose("Task '{}' requested, with_inclusions={}", name, includes)
        if includes:
            return self._task_desc(name, set())
        else:
            return self._raw_task_obj(name)
