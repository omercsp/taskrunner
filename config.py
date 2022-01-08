from common import *
from schemas import *
import os
import pathlib
import json


class Config(object):
    class _AutoDefsKeys(object):
        # Auto defintiosn keys
        TASK_ROOT = "TASK_ROOT"
        CWD = "CWD"
        CWD_REL_TASK_ROOT = "CWD_REL_TASK_ROOT"

    _CONF_FILE_NAME = "tasks.json"
    _MAJOR_VER: int = 0
    _MINOR_VER: int = 1

    @staticmethod
    def _read_tasks_file(file_path: str) -> dict:
        try:
            data: dict = json.load(open(file_path, 'r'))
            ConfigSchema.validate(data)
        except (IOError, TypeError, ValueError, TaskException) as e:
            raise TaskException("Error parsing {} - {}".format(file_path, e))
        return data

    @staticmethod
    def _check_config_file_version(data: dict, local: bool) -> None:
        conf_file_type = "local" if local else "global"
        major = data[ConfigSchema.Keys.Version][ConfigSchema.Keys.Ver.Major]
        minor = data[ConfigSchema.Keys.Version][ConfigSchema.Keys.Ver.Minor]
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

    def __init__(self, defs: list):
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
            self.defs[Config._AutoDefsKeys.TASK_ROOT] = os.path.dirname(self.local_conf_path)
            self.defs[Config._AutoDefsKeys.CWD_REL_TASK_ROOT] = os.path.relpath(
                    self.defs[Config._AutoDefsKeys.CWD], self.defs[Config._AutoDefsKeys.TASK_ROOT])
        if defs:
            for define in defs:
                key, val = parse_assignmet_str(define)
                self.defs[key] = val

        self.local_containers = self.global_conf.get(ConfigSchema.Keys.Containers, {})
        self.global_containers = self.local_conf.get(ConfigSchema.Keys.Containers, {})

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

    def visible_tasks(self) -> typing.List[str]:
        tasks = set()
        for name, task in self.global_tasks.items():
            if not task.get(TaskSchema.Keys.Hidden, False):
                tasks.add(name)
        for name, task in self.local_tasks.items():
            if not task.get(TaskSchema.Keys.Hidden, False):
                tasks.add(name)
        return list(tasks)

    #  Return anything. Types is forced by schema validations.
    def setting(self, path: str, default=None) -> typing.Any:
        setting = self.local_setting(path)
        if setting is None:
            setting = self.global_setting(path)
        return default if setting is None else setting

    @staticmethod
    def _raw_object(name, local_objects: dict, global_objects: dict):
        if name.startswith(Config.__G_PREFIX):
            return global_objects[name[len(Config.__G_PREFIX):]]
        else:
            return local_objects[name] if name in local_objects else global_objects[name]

    def raw_task(self, name: str) -> dict:
        try:
            return Config._raw_object(name, self.local_tasks, self.global_tasks)
        except KeyError:
            raise TaskException("No such task '{}'".format(name))

    def _raw_container(self, name: str) -> dict:
        try:
            return Config._raw_object(name, self.local_containers, self.global_containers)
        except KeyError:
            raise TaskException("No such task '{}'".format(name))

    @staticmethod
    def _include_obj(name, search_func, included_list: set):
        if name in included_list:
            raise TaskException("Include loop detected for '{}'".format(name))

        base_obj = search_func(name)
        included_list.add(Config.__G_PREFIX + name if name.startswith(Config.__G_PREFIX) else name)

        included_obj_name = base_obj.get(CommonKeys.Include, None)
        if included_obj_name is None:
            return base_obj

        # We about to modify the included object, so deep copy it
        included_obj_name = Config._include_obj(included_obj_name, search_func,
                                                included_list=included_list).copy()
        included_obj_name.update(base_obj)
        return included_obj_name

    def task(self, name: str, glbl: bool = False) -> dict:
        if glbl and not name.startswith(Config.__G_PREFIX):
            name = Config.__G_PREFIX + name
        hidden = self.raw_task(name).get(TaskSchema.Keys.Hidden, False)
        task = self._include_obj(name, self.raw_task, set())
        task[TaskSchema.Keys.Hidden] = hidden
        if TaskSchema.Keys.Container in task:
            task[TaskSchema.Keys.Container] = \
                self._include_obj(task[TaskSchema.Keys.Container], self._raw_container, set())
            if ContSchema.Keys.Image not in task[TaskSchema.Keys.Container]:
                raise TaskException("container setting must define an image property".format(
                            name))
        return task

    __G_PREFIX = "g/"
