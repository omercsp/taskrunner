from tr.common import *
import jsonschema


class VerValues(object):
    MAJOR: int = 4
    MINOR: int = 1


class VerKeys(object):
    Major = "major"
    Minor = "minor"


class AutoVarsKeys(object):
    TASK_ROOT = "taskRoot"
    CWD = "cwd"
    CLI_ARGS = "cliArgs"


class TaskKeys(object):
    Shell = "shell"
    ShellPath = "shell_path"
    Env = "env"
    Cwd = "cwd"
    Base = "base"
    Hidden = "hidden"
    Abstract = "abstract"
    ShortDesc = "short_desc"
    LongDesc = "description"
    Commands = "commands"
    StopOnError = "stop_on_error"
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


class GlobalKeys(object):
    Include = "include"
    UseDfltInclude = "use_default_include"
    Version = "version"
    Tasks = "tasks"
    Suppress = "suppress"
    Variables = "variables"
    DfltTask = "default_task"
    DfltShellPath = "default_shell_path"
    DfltContainerShellPath = "default_container_shell_path"
    DfltContainerTool = "default_container_tool"


_task_schema = {
    "type": "object",
    "properties": {
        TaskKeys.Base: {"type": "string", "minLength": 1},
        TaskKeys.ShortDesc: {"type": "string", "maxLength": 75},
        TaskKeys.LongDesc: {"type": "string"},
        TaskKeys.Commands: {
            "type": "array",
            "items": {"type": "string", "minLength": 1}
        },
        TaskKeys.Cwd: {"type": "string", "minLength": 1},
        TaskKeys.Shell: {"type": "boolean"},
        TaskKeys.ShellPath: {"type": "string", "minLength": 1},
        TaskKeys.Env: {
            "type": "object",
            "additionalProperties": {
                "type": "string"
            }
        },
        TaskKeys.StopOnError: {"type": "boolean"},
        TaskKeys.Hidden: {"type": "boolean"},
        TaskKeys.Abstract: {"type": "boolean"},
        TaskKeys.CImage: {"type": "string"},
        TaskKeys.CTool: {"type": "string"},
        TaskKeys.CVolumes: {
            "type": "array",
            "items": {"type": "string"}
        },
        TaskKeys.CInteractive: {"type": "boolean"},
        TaskKeys.CTty: {"type": "boolean"},
        TaskKeys.CRemove: {"type": "boolean"},
        TaskKeys.CFlags: {"type": "string"},
        TaskKeys.CExec: {"type": "boolean"},
        TaskKeys.CCwd: {"type": "string", "minLength": 1},
        TaskKeys.CShell: {"type": "boolean"},
        TaskKeys.CShellPath: {"type": "string", "minLength": 1},
        TaskKeys.CSudo: {"type": "boolean"},
        TaskKeys.CEnv: {
            "type": "object",
            "additionalProperties": {
                "type": "string"
            }
        },
        TaskKeys.Meta: {"type": "object"},
    },
    "additionalProperties": False
}

_config_file_schema = {
    "type": "object",
    "properties": {
        GlobalKeys.Version: {
            "type": "object",
            "properties": {
                VerKeys.Major: {"type": "number", "minValue": 0},
                VerKeys.Minor: {"type": "number", "minValue": 1}
            }
        },
        GlobalKeys.Include: {
            "type": "array",
            "items": {"type": "string", "minLength": 1}
        },
        GlobalKeys.UseDfltInclude: {"type": "boolean"},

        GlobalKeys.Tasks: {"type": "object"},
        GlobalKeys.Suppress: {
            "type": "array",
            "items": {"type": "string", "minLength": 1}
        },
        GlobalKeys.Variables: {"type": "object"},
        GlobalKeys.DfltTask: {"type": "string"},
        GlobalKeys.DfltShellPath: {
            "type": "string",
            "minLength": 1
        },
        GlobalKeys.DfltContainerTool: {"type": "string", "minLength": 1},
    },
    "required": [GlobalKeys.Version],
    "additionalProperties": False
}


def validate_config_file_schema(data: dict) -> None:
    try:
        jsonschema.validate(data, _config_file_schema)
    except jsonschema.ValidationError as e:
        raise TaskException("Schema validation error at '{}': {}".format(
            "/".join(str(v) for v in list(e.absolute_path)), e.message))


def validate_task_schema(name: str, data: dict) -> None:
    try:
        jsonschema.validate(data, _task_schema)
    except jsonschema.ValidationError as e:
        raise TaskException(f"Task schema validation error for '{name}': {e.message}")


def dump_config_file_schema() -> None:
    print_dict(_config_file_schema)


def dump_task_schema() -> None:
    print_dict(_task_schema)
