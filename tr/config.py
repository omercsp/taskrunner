from tr.schemas import *
from tr.common import *
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
            raise TaskException(f"Error parsing {file_path} - {e}")
        return data

    def _check_config_file_version(self, path: str) -> None:
        major = self.conf[GlobalKeys.Version][VerKeys.Major]
        minor = self.conf[GlobalKeys.Version][VerKeys.Minor]
        if major != VerValues.MAJOR or minor > VerValues.MINOR:
            raise TaskException(
                f"Incompatible major configuration version for '{path}': " +
                f"Found:{major}.{minor}, expected <= {VerValues.MAJOR,}.{VerValues.MINOR}")
        if minor != VerValues.MINOR:
            print(f"Incompatible minor configuration version for '{VerValues.MINOR}'")

    def _read_configuration(self, file_path: str, read_files: set = set()):
        conf = {}
        tasks = {}
        defs = {}
        info("Reading configuration file {}", file_path)
        orig_conf = Config._read_tasks_file(file_path)
        includes = orig_conf.get(GlobalKeys.Include, [])
        if file_path != _DFLT_CONF_FILE_NAME and \
                os.path.isfile(_DFLT_CONF_FILE_NAME) and \
                orig_conf.get(GlobalKeys.UseDfltInclude, True):
            includes.insert(0, _DFLT_CONF_FILE_NAME)

        info("Configuration file includes: {}", includes)
        read_files.add(file_path)
        for f in includes:
            f = self.expander(f)
            if f in read_files:
                raise TaskException(f"Include loop detected - '{f}'")
            included_conf = self._read_configuration(f, read_files)
            tasks.update(included_conf.get(GlobalKeys.Tasks))
            defs.update(included_conf.get(GlobalKeys.Variables))
            conf.update(included_conf)
        read_files.remove(file_path)
        if GlobalKeys.Include in conf:
            conf.pop(GlobalKeys.Include)

        conf.update(orig_conf)
        tasks.update(orig_conf.get(GlobalKeys.Tasks, {}))
        for supressed_task in conf.get(GlobalKeys.Suppress, []):
            if supressed_task in tasks:
                info("Removing suppressed task {}", supressed_task)
                tasks.pop(supressed_task)
        conf[GlobalKeys.Tasks] = tasks
        defs.update(orig_conf.get(GlobalKeys.Variables, {}))
        conf[GlobalKeys.Variables] = defs
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

    def __init__(self, cli_conf: typing.Union[str, None], cli_defs: list,
                 cli_args: typing.List[str]):
        self.expander = StringVarExpander()
        conf_path = Config._get_conf_file_path(cli_conf)

        #  Populate some variables early so they are available in
        early_vars = {}
        cwd = os.getcwd()
        early_vars[AutoVarsKeys.CWD] = cwd
        if conf_path:
            early_vars[AutoVarsKeys.TASK_ROOT] = os.path.dirname(conf_path)
        else:
            early_vars[AutoVarsKeys.TASK_ROOT] = cwd

        self.conf = {}
        if conf_path:
            self.expander.map = early_vars
            self.conf = self._read_configuration(conf_path)
            validate_config_file_schema(self.conf)
            self._check_config_file_version(conf_path)

        #  Always override configuration variables with hard coded ones
        self.vars = self.conf.get(GlobalKeys.Variables, {})
        self.vars.update(early_vars)
        self.tasks = self.conf.get(GlobalKeys.Tasks, {})
        self.vars[AutoVarsKeys.CLI_ARGS] = " ".join(cli_args)
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
        return self.setting(GlobalKeys.DfltTask)

    def default_container_tool(self) -> str:
        return self.setting(GlobalKeys.DfltContainerTool, default="/usr/bin/docker")

    def default_container_shell_path(self) -> str:
        return self.setting(GlobalKeys.DfltContainerShellPath, default="/usr/bin/sh")

    def default_shell_path(self) -> typing.Union[str, None]:
        return self.setting(GlobalKeys.DfltShellPath, None)

    def visible_tasks(self) -> typing.List[str]:
        tasks = set()
        for name, task in self.tasks.items():
            if not task.get(TaskKeys.Hidden, False):
                tasks.add(name)
        return list(tasks)

    #  Return anything. Types is forced by schema validations.
    def setting(self, path: str, default=None) -> typing.Any:
        return dict_value(self.conf, path, default=default)

    def _raw_task_obj(self, name: str) -> dict:
        try:
            return self.tasks[name]
        except KeyError:
            raise TaskException(f"No such task '{name}'")

    def _task_desc(self, name, included_list: set):
        if name in included_list:
            raise TaskException(f"Include loop detected for '{name}'")

        base_task = self._raw_task_obj(name)
        hidden = base_task.get(TaskKeys.Hidden, False)
        abstract = base_task.get(TaskKeys.Abstract, False)

        included_task = base_task.get(TaskKeys.Base, None)
        if included_task is None:
            return base_task

        # We about to modify the included object, so deep copy it
        included_task = self._task_desc(
            included_task, included_list=included_list).copy()
        included_task.update(base_task)
        included_task[TaskKeys.Hidden] = hidden
        included_task[TaskKeys.Abstract] = abstract
        return included_task

    def get_task_desc(self, name: str, includes: bool):
        verbose("Task '{}' requested, with_inclusions={}", name, includes)
        if includes:
            return self._task_desc(name, set())
        else:
            return self._raw_task_obj(name)
