from common import *
import jsonschema


class CommonKeys(object):
    Shell = "shell"
    ShellPath = "shell_path"
    Env = "env"
    Cwd = "cwd"
    Include = "include"
    Hidden = "hidden"


class ContSchema(object):
    class Keys(object):
        Image = "image"
        Tool = "container_tool"
        Volumes = "volumes"
        Interactive = "interactive"
        Tty = "tty"
        Flags = "flags"
        Exec = "exec"
        Remove = "remove"
        Shell = CommonKeys.Shell
        ShellPath = CommonKeys.ShellPath
        Env = CommonKeys.Env
        Cwd = CommonKeys.Cwd
        Include = CommonKeys.Include

    schema = {
        "type": "object",
        "properties": {
            Keys.Include: {"type": "string", "minLength": 1},
            Keys.Image: {"type": "string", "minLength": 1},
            Keys.Tool: {"type": "string"},
            Keys.Volumes: {
                "type": "array",
                "items": {"type": "string"}
            },
            Keys.Interactive: {"type": "boolean"},
            Keys.Tty: {"type": "boolean"},
            Keys.Remove: {"type": "boolean"},
            Keys.Flags: {"type": "string"},
            Keys.Exec: {"type": "boolean"},
            Keys.Cwd: {"type": "string", "minLength": 1},
            Keys.Shell: {"type": "boolean"},
            Keys.ShellPath: {"type": "string", "minLength": 1},
            Keys.Env: {
                "type": "object",
                "additionalProperties": {
                    "type": "string"
                }
            },
        },
        "additionalProperties": False
    }


class TaskSchema(object):
    class Keys(object):
        Include = CommonKeys.Include
        Shell = CommonKeys.Shell
        ShellPath = CommonKeys.ShellPath
        Env = CommonKeys.Env
        Cwd = CommonKeys.Cwd
        Hidden = CommonKeys.Hidden
        ShortDesc = "short_desc"
        LongDesc = "description"
        Commands = "commands"
        StopOnError = "stop_on_error"
        Container = "container"
        Global = "global"
    schema = {
        "type": "object",
        "properties": {
            Keys.Include: {"type": "string", "minLength": 1},
            Keys.ShortDesc: {"type": "string", "maxLength": 75},
            Keys.LongDesc: {"type": "string"},
            Keys.Commands: {
                "type": "array",
                "items": {"type": "string", "minLength": 1}
            },
            Keys.Cwd: {"type": "string", "minLength": 1},
            Keys.Shell: {"type": "boolean"},
            Keys.ShellPath: {"type": "string", "minLength": 1},
            Keys.Env: {
                "type": "object",
                "additionalProperties": {
                    "type": "string"
                }
            },
            Keys.StopOnError: {"type": "boolean"},
            Keys.Container: {"type": "string", "minLength": 1},
            Keys.Hidden: {"type": "boolean"},
            Keys.Global: {"type": "boolean"},
        },
        "additionalProperties": False
    }


class ConfigSchema(object):
    class Keys(object):
        class Ver(object):
            Major = "major"
            Minor = "minor"
        Version = "version"
        Tasks = "tasks"
        Containers = "containers"
        Definitions = "definitions"
        DfltTask = "default_task"
        DfltShellPath = "default_shell_path"
        DfltContainerShellPath = "default_container_shell_path"
        DfltContainerTool = "default_container_tool"
        AllowGlobal = "allow_global"
    schema = {
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
                "additionalProperties": TaskSchema.schema
             },
            Keys.Containers:  {
                "type": "object",
                "additionalProperties": ContSchema.schema
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
            jsonschema.validate(data, ConfigSchema.schema)
        except jsonschema.ValidationError as e:
            raise TaskException("Schema validation error at '{}': {}".format(
                "/".join(str(v) for v in list(e.absolute_path)), e.message))
