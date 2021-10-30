from common import *
from schemas import *
import os
import pathlib
import json
import jsonschema


def print_dict(d: dict):
    print(json.dumps(d, indent=4))


class Config(object):
    class _AutoDefsKeys(object):
        # Auto defintiosn keys
        CONF_PATH = "CONF_PATH"
        CWD = "CWD"
        CWD_REL_CONF = "CWD_REL_CONF"

    _CONF_FILE_NAME = "task_runner.json"
    _MAJOR_VER: int = 0
    _MINOR_VER: int = 1

    @staticmethod
    def _read_tasks_file(file_path: str) -> dict:
        try:
            data: dict = json.load(open(file_path, 'r'))
            jsonschema.validate(data, schema=ConfigScheme.schema)
            return data
        except (IOError, TypeError, ValueError, jsonschema.ValidationError) as e:
            raise TaskException("Error parsing {} - {}".format(file_path, e))

    @staticmethod
    def _check_config_file_version(data: dict, local: bool) -> None:
        conf_file_type = "local" if local else "global"
        major = data["version"]["major"]
        minor = data["version"]["minor"]
        if major != Config._MAJOR_VER or minor > Config._MINOR_VER:
            raise TaskException(("Incompatible {} configuration file version: " +
                                 "Found:{}.{}, expected <= {}.{}").format(
                conf_file_type, major, minor, Config._MAJOR_VER, Config._MINOR_VER))
        if minor != Config._MINOR_VER:
            print("Incompatible {} configuration file minor version".format(conf_file_type))

    def _read_local_conf_file(self) -> typing.Tuple[dict, str]:
        directory = os.getcwd()
        f = directory + "/" + Config._CONF_FILE_NAME
        while not os.path.exists(f):
            if directory == "/":
                return {}, ""
            directory = os.path.dirname(directory)
            f = directory + "/" + Config._CONF_FILE_NAME
        data = Config._read_tasks_file(f)
        Config._check_config_file_version(data, local=True)
        return data, f

    def _read_global_conf_file(self):
        f = str(pathlib.Path.home()) + "/.config/" + Config._CONF_FILE_NAME
        if not os.path.isfile(f):
            return {}, ""
        data = Config._read_tasks_file(f)
        Config._check_config_file_version(data, local=False)
        return data, f

    def __init__(self):
        self.global_conf, self.global_conf_path = self._read_global_conf_file()
        self.local_conf, self.local_conf_path = self._read_local_conf_file()

        self.global_tasks = self.global_conf.get(ConfigScheme.Keys.Tasks, {})
        self.local_tasks = self.local_conf.get(ConfigScheme.Keys.Tasks, {})

        self.defs = self.global_conf.get(ConfigScheme.Keys.Definitions, {})
        self.defs.update(self.local_conf.get(ConfigScheme.Keys.Definitions, {}))

        self.defs[Config._AutoDefsKeys.CWD] = os.getcwd()
        if self.local_conf:
            self.defs[Config._AutoDefsKeys.CONF_PATH] = os.path.dirname(self.local_conf_path)
            self.defs[Config._AutoDefsKeys.CWD_REL_CONF] = os.path.relpath(
                    self.defs[Config._AutoDefsKeys.CWD], self.defs[Config._AutoDefsKeys.CONF_PATH])

        self.containers = self.global_conf.get(ConfigScheme.Keys.Containers, {})
        self.containers.update(self.local_conf.get(ConfigScheme.Keys.Containers, {}))

        self.supressed_tasks = self.global_conf.get(ConfigScheme.Keys.Supress, [])
        self.supressed_tasks += self.local_conf.get(ConfigScheme.Keys.Supress, [])

    def local_setting(self, path: str):
        return dict_value(self.local_conf, path)

    def global_setting(self, path: str):
        return dict_value(self.global_conf, path)

    def default_task_name(self) -> typing.Union[str, None]:
        return self.setting(ConfigScheme.Keys.DfltTask)

    def default_container_tool(self) -> str:
        return self.setting(ConfigScheme.Keys.DfltContainerTool, default="/usr/bin/docker")

    def default_shell_path(self) -> typing.Union[str, None]:
        return self.setting(ConfigScheme.Keys.DfltShellPath)

    #  Return anything. Types is forced by schema validations.
    def setting(self, path: str, default=None) -> typing.Any:
        setting = self.local_setting(path)
        if setting is None:
            setting = self.global_setting(path)
        return default if setting is None else setting

    def _raw_task(self, name: str) -> typing.Any:
        if name is None:
            raise TaskException("No task name was given")
        try:
            if name.startswith("global/"):
                task = self.global_tasks[name[7:]]
            else:
                task = self.local_tasks[name]
        except KeyError:
            return None
        return task

    def _include(self, task: dict, to_include: list, included_list: list):
        for t_name in to_include:
            if t_name in included_list:
                continue
            t = self._raw_task(t_name)
            if t is None:
                raise TaskException("Unknown included task '{}'".format(t_name))
            included_list.append(t_name)
            self._include(t, t.get(ConfigScheme.Keys.Include, []), included_list)
            task.update(t)

    def task(self, name: str) -> dict:
        main_task = self.local_tasks.get(name, self.global_tasks.get(name, None))
        if main_task is None or name in self.supressed_tasks:
            raise TaskException("No such task '{}'".format(name))

        task = {}
        try:
            self._include(task, main_task.get(ConfigScheme.Keys.Include, []), [])
        except TaskException as e:
            raise TaskException("Error parsing task '{}' - {}".format(name, e))
        task.update(main_task)
        try:
            jsonschema.validate(task, schema=TaskSchema.schema)
        except (jsonschema.ValidationError) as e:
            raise TaskException("Error parsing task '{}' - {}".format(name, e))
        container = task.get(TaskSchema.Keys.Container, None)
        if container is not None:
            try:
                task[TaskSchema.Keys.Container] = self.containers[container]
            except KeyError:
                raise TaskException("Unknown container setting '{}' for task '{}'".format(
                    container, name))
        task.pop(ConfigScheme.Keys.Include, None)
        return task
