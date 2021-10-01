from common import *
import os
import pathlib
import json
import jsonschema


def print_dict(d: dict):
    print(json.dumps(d, indent=4))


class TaskKeys(object):
    SHORT_DESC = "short_desc"
    LONG_DESC = "description"
    COMMANDS = "commands"
    SHELL = "shell"
    STOP_ON_ERROR = "stop_on_error"
    ENV = "env"


class Config(object):
    _CONF_FILE_NAME = "/task_runner.json"
    _TASKS_KEY = "tasks"
    _DEFS_KEY = "definitions"
    _INCLUDE_KEY = "include"
    DEFAULT_TASK = "default_task"
    SUPRESS_KEY = "supress"

    _TASK_SCHEMA = {
        "type": "object",
        "properties": {
            TaskKeys.SHORT_DESC: {
                "type": "string",
                "maxLength": 75
            },
            TaskKeys.LONG_DESC: {"type": "string"},
            TaskKeys.COMMANDS:
                {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "minItems": 1
                },
            TaskKeys.SHELL: {"type": "boolean"},
            TaskKeys.ENV : {
                "type": "object",
                "additionalProperties" : {
                    "type": "string"
                }
            }
        },
        "required": [TaskKeys.COMMANDS, TaskKeys.SHELL, TaskKeys.STOP_ON_ERROR]
    }
    _CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            _DEFS_KEY: {"type": "object"},
            DEFAULT_TASK: {"type": "string"},
            _TASKS_KEY: {"type": "object"},
            SUPRESS_KEY: {
                "type": "array",
                "items": {
                    "type": "string",
                    "minLength": 1
                }
            }
        }
    }

    @staticmethod
    def _read_tasks_file(file_path: str) -> dict:
        try:
            conf_file = json.load(open(file_path, 'r'))
            jsonschema.validate(conf_file, schema=Config._CONFIG_SCHEMA)
            return conf_file
        except (IOError, TypeError, ValueError, jsonschema.ValidationError) as e:
            raise TaskException("Error parsing {} - {}".format(file_path, e))

    def _read_local_conf_file(self):
        directory = os.getcwd()
        f = directory + Config._CONF_FILE_NAME
        while not os.path.exists(f):
            if directory == "/":
                return
            directory = os.path.dirname(directory)
            f = directory + Config._CONF_FILE_NAME
        self.local_conf = self._read_tasks_file(f)

    def _read_global_conf_file(self):
        f = str(pathlib.Path.home()) + "/.config/" + Config._CONF_FILE_NAME
        if not os.path.isfile(f):
            return
        self.global_conf = self._read_tasks_file(f)

    def __init__(self):
        self._read_global_conf_file()
        self._read_local_conf_file()

        self.global_tasks = self.global_conf.get(Config._TASKS_KEY, {})
        self.local_tasks = self.local_conf.get(Config._TASKS_KEY, {})

        self.defs = self.global_conf.get(Config._DEFS_KEY, {})
        self.defs.update(self.local_conf.get(Config._DEFS_KEY, {}))

        self.supressed_tasks = self.global_conf.get(Config.SUPRESS_KEY, [])
        self.supressed_tasks += self.local_conf.get(Config.SUPRESS_KEY, [])

    def local_setting(self, path: str):
        return json_dict_value(self.local_conf, path)

    def global_setting(self, path: str):
        return json_dict_value(self.global_conf, path)

    #  Return anything. Types is forced by schema validations.
    def setting(self, path: str, default=None) -> typing.Any:
        setting = self.local_setting(path)
        if setting is not None:
            return setting
        if setting is not None:
            self.global_setting(path)
        return default

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
            self._include(t, t.get(Config._INCLUDE_KEY, []), included_list)
            task.update(t)

    def task(self, name: str) -> dict:
        main_task = self.local_tasks.get(name, self.global_tasks.get(name, None))
        if main_task is None or name in self.supressed_tasks:
            raise TaskException("No such task '{}'".format(name))

        task = {}
        try:
            self._include(task, main_task.get(Config._INCLUDE_KEY, []), [])
        except TaskException as e:
            raise TaskException("Error parsing task '{}' - {}".format(name, e))
        task.update(main_task)
        task.setdefault(TaskKeys.SHELL, False)
        task.setdefault(TaskKeys.STOP_ON_ERROR, True)
        task.setdefault(TaskKeys.COMMANDS, [])
        task.setdefault(TaskKeys.ENV, {})
        try:
            jsonschema.validate(task, schema=Config._TASK_SCHEMA)
        except (jsonschema.ValidationError) as e:
            raise TaskException("Error parsing task '{}' - {}".format(name, e))
        task.pop(Config._INCLUDE_KEY, None)
        return task
