from common import *
import jsonschema


class Schema(object):
    class Version(object):
        MAJOR: int = 1
        MINOR: int = 0

    class Keys(object):
        class Ver(object):
            Major = "major"
            Minor = "minor"

        class AutoDefs(object):
            TASK_ROOT = "TASK_ROOT"
            CWD = "CWD"
            CWD_REL_TASK_ROOT = "CWD_REL_TASK_ROOT"
            CLI_ARGS = "ARGS"

        class Task(object):
            Shell = "shell"
            ShellPath = "shell_path"
            Env = "env"
            Cwd = "cwd"
            Include = "include"
            Hidden = "hidden"
            ShortDesc = "short_desc"
            LongDesc = "description"
            Commands = "commands"
            StopOnError = "stop_on_error"
            Global = "global"
            Meta = "meta"
            # Container settings
            CImage = "c_image"
            CTool = "c_container_tool"
            CVolumes = "c_volumes"
            CInteractive = "c_interactive"
            CTty = "c_tty"
            CFlags = "c_flags"
            CExec = "c_exec"
            CRemove = "c_remove"
            CSudo = "c_sudo"
            CShell = "c_shell"
            CShellPath = "c_shell_path"
            CEnv = "c_env"
            CCwd = "c_cwd"

        Version = "version"
        Tasks = "tasks"
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
            Keys.Task.Hidden: {"type": "boolean"},
            Keys.Task.Global: {"type": "boolean"},
            Keys.Task.CImage: {"type": "string"},
            Keys.Task.CTool: {"type": "string"},
            Keys.Task.CVolumes: {
                "type": "array",
                "items": {"type": "string"}
            },
            Keys.Task.CInteractive: {"type": "boolean"},
            Keys.Task.CTty: {"type": "boolean"},
            Keys.Task.CRemove: {"type": "boolean"},
            Keys.Task.CFlags: {"type": "string"},
            Keys.Task.CExec: {"type": "boolean"},
            Keys.Task.CCwd: {"type": "string", "minLength": 1},
            Keys.Task.CShell: {"type": "boolean"},
            Keys.Task.CShellPath: {"type": "string", "minLength": 1},
            Keys.Task.CSudo: {"type": "boolean"},
            Keys.Task.CEnv: {
                "type": "object",
                "additionalProperties": {
                    "type": "string"
                }
            },
            Keys.Task.Meta: {"type": "object"},
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
