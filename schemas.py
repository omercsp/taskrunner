from common import *
import jsonschema


class _CommonKeys(object):
    Shell = "shell"
    ShellPath = "shell_path"
    Env = "env"
    Cwd = "cwd"
    Include = "include"
    Hidden = "hidden"


class Schema(object):
    class Keys(object):
        class Ver(object):
            Major = "major"
            Minor = "minor"

        class Task(object):
            Include = _CommonKeys.Include
            Shell = _CommonKeys.Shell
            ShellPath = _CommonKeys.ShellPath
            Env = _CommonKeys.Env
            Cwd = _CommonKeys.Cwd
            Hidden = _CommonKeys.Hidden
            ShortDesc = "short_desc"
            LongDesc = "description"
            Commands = "commands"
            StopOnError = "stop_on_error"
            Container = "container"
            Global = "global"

        class Container(object):
            Image = "image"
            Tool = "container_tool"
            Volumes = "volumes"
            Interactive = "interactive"
            Tty = "tty"
            Flags = "flags"
            Exec = "exec"
            Remove = "remove"
            Sudo = "sudo"
            Shell = _CommonKeys.Shell
            ShellPath = _CommonKeys.ShellPath
            Env = _CommonKeys.Env
            Cwd = _CommonKeys.Cwd
            Include = _CommonKeys.Include
        Version = "version"
        Tasks = "tasks"
        Containers = "containers"
        Definitions = "definitions"
        DfltTask = "default_task"
        DfltShellPath = "default_shell_path"
        DfltContainerShellPath = "default_container_shell_path"
        DfltContainerTool = "default_container_tool"
        AllowGlobal = "allow_global"

    __task_schema = {
        "type": "object",
        "properties": {
            Keys.Task.Include: {"type": "string", "minLength": 1},
            Keys.Task.ShortDesc: {"type": "string", "maxLength": 75},
            Keys.Task.LongDesc: {"type": "string"},
            Keys.Task.Commands: {
                "type": "array",
                "items": {"type": "string", "minLength": 1}
            },
            Keys.Task.Cwd: {"type": "string", "minLength": 1},
            Keys.Task.Shell: {"type": "boolean"},
            Keys.Task.ShellPath: {"type": "string", "minLength": 1},
            Keys.Task.Env: {
                "type": "object",
                "additionalProperties": {
                    "type": "string"
                }
            },
            Keys.Task.StopOnError: {"type": "boolean"},
            Keys.Task.Container: {"type": "string", "minLength": 1},
            Keys.Task.Hidden: {"type": "boolean"},
            Keys.Task.Global: {"type": "boolean"},
        },
        "additionalProperties": False
    }

    __container_schema = {
        "type": "object",
        "properties": {
            Keys.Container.Include: {"type": "string", "minLength": 1},
            Keys.Container.Image: {"type": "string", "minLength": 1},
            Keys.Container.Tool: {"type": "string"},
            Keys.Container.Volumes: {
                "type": "array",
                "items": {"type": "string"}
            },
            Keys.Container.Interactive: {"type": "boolean"},
            Keys.Container.Tty: {"type": "boolean"},
            Keys.Container.Remove: {"type": "boolean"},
            Keys.Container.Flags: {"type": "string"},
            Keys.Container.Exec: {"type": "boolean"},
            Keys.Container.Cwd: {"type": "string", "minLength": 1},
            Keys.Container.Shell: {"type": "boolean"},
            Keys.Container.ShellPath: {"type": "string", "minLength": 1},
            Keys.Container.Sudo: {"type": "boolean"},
            Keys.Container.Env: {
                "type": "object",
                "additionalProperties": {
                    "type": "string"
                }
            },
        },
        "additionalProperties": False
    }
    __schema = {
        "type": "object",
        "properties": {
            Keys.Version: {
                "type": "object",
                "properties": {
                    Keys.Ver.Major: {"type": "number", "minValue": 0},
                    Keys.Ver.Minor: {"type": "number", "minValue": 1}
                }
            },
            Keys.Tasks: {
                "type": "object",
                "additionalProperties": __task_schema
             },
            Keys.Containers:  {
                "type": "object",
                "additionalProperties": __container_schema
            },
            Keys.Definitions: {"type": "object"},
            Keys.DfltTask: {"type": "string"},
            Keys.DfltShellPath: {
                "type": "string",
                "minLength": 1
            },
            Keys.DfltContainerTool: {"type": "string", "minLength": 1},
            Keys.AllowGlobal: {"type": "boolean"}
        },
        "required": [Keys.Version],
        "additionalProperties": False
    }

    @staticmethod
    def validate(data: dict) -> None:
        try:
            jsonschema.validate(data, Schema.__schema)
        except jsonschema.ValidationError as e:
            raise TaskException("Schema validation error at '{}': {}".format(
                "/".join(str(v) for v in list(e.absolute_path)), e.message))

    @staticmethod
    def dump() -> None:
        print_dict(Schema.__schema)
