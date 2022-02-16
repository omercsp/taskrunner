from schemas import Schema
from common import *
import os
import pathlib
import json


# None schema keys
class ExtKeys(object):
    Global = "global"


class Config(object):
    class _AutoDefsKeys(object):
        # Auto definitions keys
        TASK_ROOT = "TASK_ROOT"
        CWD = "CWD"
        CWD_REL_TASK_ROOT = "CWD_REL_TASK_ROOT"

    __G_PREFIX = "g/"
    _CONF_FILE_NAME = "tasks.json"
    _MAJOR_VER: int = 0
    _MINOR_VER: int = 1

    @staticmethod
    def _read_tasks_file(file_path: str) -> dict:
        try:
            data: dict = json.load(open(file_path, 'r'))
            Schema.validate(data)
        except (IOError, TypeError, ValueError, TaskException) as e:
            raise TaskException("Error parsing {} - {}".format(file_path, e))
        return data

    @staticmethod
    def _check_config_file_version(data: dict, local: bool) -> None:
        conf_file_type = "local" if local else "global"
        major = data[Schema.Keys.Version][Schema.Keys.Ver.Major]
        minor = data[Schema.Keys.Version][Schema.Keys.Ver.Minor]
        if major != Config._MAJOR_VER or minor > Config._MINOR_VER:
            raise TaskException(("Incompatible {} configuration file version: " +
                                 "Found:{}.{}, expected <= {}.{}").format(
                conf_file_type, major, minor, Config._MAJOR_VER, Config._MINOR_VER))
        if minor != Config._MINOR_VER:
            print("Incompatible {} configuration file minor version".format(conf_file_type))

    def _read_local_conf_file(self) -> None:
        directory = os.getcwd()
        f = directory + "/." + Config._CONF_FILE_NAME
        info("Reading '{}'".format(f))
        while not os.path.exists(f):
            if directory == "/":
                self.local_conf = {}
                self.local_conf_path = ""
                return
            directory = os.path.dirname(directory)
            f = directory + "/." + Config._CONF_FILE_NAME
        self.local_conf_path = f
        self.local_conf = Config._read_tasks_file(f)
        Config._check_config_file_version(self.local_conf, local=True)

    def _read_global_conf_file(self) -> None:
        f = str(pathlib.Path.home()) + "/.config/" + Config._CONF_FILE_NAME
        info("Reading '{}'".format(f))
        if not os.path.isfile(f):
            self.global_conf = {}
            self.global_conf_path = ""
            return
        self.global_conf_path = f
        self.global_conf = Config._read_tasks_file(f)
        Config._check_config_file_version(self.global_conf, local=False)

    def __init__(self, defs: list):
        self._read_global_conf_file()
        self._read_local_conf_file()

        self.global_tasks = self.global_conf.get(Schema.Keys.Tasks, {})
        for task in self.global_tasks.values():
            task[Schema.Keys.Task.Global] = True
        self.local_tasks = self.local_conf.get(Schema.Keys.Tasks, {})
        for task in self.local_tasks.values():
            task[Schema.Keys.Task.Global] = False

        self.defs = self.global_conf.get(Schema.Keys.Definitions, {})
        self.defs.update(self.local_conf.get(Schema.Keys.Definitions, {}))

        self.defs[Config._AutoDefsKeys.CWD] = os.getcwd()
        if self.local_conf:
            self.defs[Config._AutoDefsKeys.TASK_ROOT] = os.path.dirname(self.local_conf_path)
            self.defs[Config._AutoDefsKeys.CWD_REL_TASK_ROOT] = os.path.relpath(
                    self.defs[Config._AutoDefsKeys.CWD], self.defs[Config._AutoDefsKeys.TASK_ROOT])
        if defs:
            for define in defs:
                key, val = parse_assignment_str(define)
                self.defs[key] = val
        if logging_enabled_for(logging.DEBUG):
            verbose("Definitions settings are (unexpanded):")
            start_raw_logging()
            for k,v in self.defs.items():
                verbose("{}='{}'", k, v)
            stop_raw_logging()

        self.local_containers = self.local_conf.get(Schema.Keys.Containers, {})
        self.global_containers = self.global_conf.get(Schema.Keys.Containers, {})

    def allow_global(self):
        return self.local_conf.get(Schema.Keys.AllowGlobal, True) and \
               self.global_conf.get(Schema.Keys.AllowGlobal, True)

    def local_setting(self, path: str):
        return dict_value(self.local_conf, path)

    def global_setting(self, path: str):
        return dict_value(self.global_conf, path)

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
        for name, task in self.global_tasks.items():
            if not task.get(Schema.Keys.Task.Hidden, False):
                tasks.add(name)
        for name, task in self.local_tasks.items():
            if not task.get(Schema.Keys.Task.Hidden, False):
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
        global_prefix = name.startswith(Config.__G_PREFIX)
        if global_prefix or name not in local_objects:
            if global_prefix:
                name = name[len(Config.__G_PREFIX):]
            obj = global_objects[name]
            obj[ExtKeys.Global] = True
        else:
            obj = local_objects[name]
            obj[ExtKeys.Global] = False
        return obj

    def raw_task(self, name: str) -> dict:
        try:
            return Config._raw_object(name, self.local_tasks, self.global_tasks)
        except KeyError:
            raise TaskException("No such task '{}'".format(name))

    def _raw_container(self, name: str) -> dict:
        try:
            return Config._raw_object(name, self.local_containers, self.global_containers)
        except KeyError:
            raise TaskException("No such container '{}'".format(name))

    @staticmethod
    def _include_obj(name, search_func, included_list: set):
        if name in included_list:
            raise TaskException("Include loop detected for '{}'".format(name))

        base_obj = search_func(name)
        hidden = base_obj.get(Schema.Keys.Task.Hidden, False)
        included_list.add(Config.__G_PREFIX + name if name.startswith(Config.__G_PREFIX) else name)

        included_obj_name = base_obj.get(Schema.Keys.Task.Include, None)
        if included_obj_name is None:
            return base_obj

        # We about to modify the included object, so deep copy it
        included_obj_name = Config._include_obj(included_obj_name, search_func,
                                                included_list=included_list).copy()
        included_obj_name.update(base_obj)
        included_obj_name[Schema.Keys.Task.Hidden] = hidden
        return included_obj_name

    def container_descriptor(self, name: str) -> dict:
        verbose("Container '{}' requested", name)
        return self._include_obj(name, self._raw_container, set())

    def task_descriptor(self, name: str, force_global: bool = False) -> dict:
        verbose("Task '{}' requested. force_global={}", name, force_global)
        if force_global and not name.startswith(Config.__G_PREFIX):
            name = Config.__G_PREFIX + name
        return self._include_obj(name, self.raw_task, set())
