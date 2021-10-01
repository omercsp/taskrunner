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

    _CONF_FILE_NAME = "tasks.json"
    _MAJOR_VER: int = 0
    _MINOR_VER: int = 1

    @staticmethod
    def _read_tasks_file(file_path: str) -> dict:
        try:
            data: dict = json.load(open(file_path, 'r'))
            jsonschema.validate(data, schema=ConfigSchema.schema)
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
        f = directory + "/." + Config._CONF_FILE_NAME
        while not os.path.exists(f):
            if directory == "/":
                return {}, ""
            directory = os.path.dirname(directory)
            f = directory + "/." + Config._CONF_FILE_NAME
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

        self.global_tasks = self.global_conf.get(ConfigSchema.Keys.Tasks, {})
        for task in self.global_tasks.values():
            task[TaskSchema.Keys.Global] = True
        self.local_tasks = self.local_conf.get(ConfigSchema.Keys.Tasks, {})
        for task in self.local_tasks.values():
            task[TaskSchema.Keys.Global] = False

        self.defs = self.global_conf.get(ConfigSchema.Keys.Definitions, {})
        self.defs.update(self.local_conf.get(ConfigSchema.Keys.Definitions, {}))

        self.defs[Config._AutoDefsKeys.CWD] = os.getcwd()
        if self.local_conf:
            self.defs[Config._AutoDefsKeys.CONF_PATH] = os.path.dirname(self.local_conf_path)
            self.defs[Config._AutoDefsKeys.CWD_REL_CONF] = os.path.relpath(
                    self.defs[Config._AutoDefsKeys.CWD], self.defs[Config._AutoDefsKeys.CONF_PATH])

        self.containers = self.global_conf.get(ConfigSchema.Keys.Containers, {})
        self.containers.update(self.local_conf.get(ConfigSchema.Keys.Containers, {}))

    def allow_global(self):
        return self.local_conf.get(ConfigSchema.Keys.AllowGlobal, True) and \
               self.global_conf.get(ConfigSchema.Keys.AllowGlobal, True)

    def local_setting(self, path: str):
        return dict_value(self.local_conf, path)

    def global_setting(self, path: str):
        return dict_value(self.global_conf, path)

    def default_task_name(self) -> typing.Union[str, None]:
        return self.setting(ConfigSchema.Keys.DfltTask)

    def default_container_tool(self) -> str:
        return self.setting(ConfigSchema.Keys.DfltContainerTool, default="/usr/bin/docker")

    def default_container_shell_path(self) -> str:
        return self.setting(ConfigSchema.Keys.DfltContainerShellPath, default="/usr/bin/sh")

    def default_shell_path(self) -> typing.Union[str, None]:
        return self.setting(ConfigSchema.Keys.DfltShellPath, None)

    #  Return anything. Types is forced by schema validations.
    def setting(self, path: str, default=None) -> typing.Any:
        setting = self.local_setting(path)
        if setting is None:
            setting = self.global_setting(path)
        return default if setting is None else setting

    def _include(self, name: str, task: dict, to_include: list, included_list: list):
        for inc_task_name in to_include:
            if inc_task_name in included_list:
                continue
            task_search_name, glbl = task_name_and_global(inc_task_name)
            t = self.task(task_search_name, glbl=glbl, raw=True)
            if t is None:
                raise TaskException("Error parsing '{}' - unknown included task '{}'".format(
                    name, inc_task_name))
            t = t.copy()
            included_list.append(inc_task_name)
            self._include(name, t, t.get(TaskSchema.Keys.Include, []), included_list)
            task.update(t)

    def task(self, name: str, glbl: bool = False, raw: bool = False) -> dict:
        def _validate_task(task):
            try:
                jsonschema.validate(task, schema=TaskSchema.schema)
            except (jsonschema.ValidationError) as e:
                raise TaskException("Error parsing task '{}' - {}".format(name, e))

        if glbl:
            base_task = self.global_tasks.get(name, None)
        else:
            base_task = self.local_tasks.get(name, self.global_tasks.get(name, None))

        if base_task is None:
            raise TaskException("No such task '{}'".format(name))
        if raw:
            return base_task

        task = {}
        self._include(name, task, base_task.get(TaskSchema.Keys.Include, []), [])
        task.update(base_task)

        task.pop(TaskSchema.Keys.Include, None)
        if TaskSchema.Keys.Abstract not in base_task:
            task[TaskSchema.Keys.Abstract] = False
        _validate_task(task)
        return task

def task_name_and_global(name) -> typing.Tuple[str, bool]:
    if name.startswith(TaskSchema.Keys.Global + "/"):
        return name[7:], True
    else:
        return name, False

