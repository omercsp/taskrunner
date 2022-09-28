from tr.common import *
import jsonschema


class VerValues(object):
    MAJOR: int = 4
    MINOR: int = 4


class VerKeys(object):
    Major = "major"
    Minor = "minor"


class _CommonKeys(object):
    Variables = "variables"


class AutoVarsKeys(object):
    TASK_ROOT = "taskRoot"
    CWD = "cwd"
    TASK_CLI_ARGS = "cliArgs"


class TaskKeys(object):
    Shell = "shell"
    ShellPath = "shell_path"
    Env = "env"
    EnvInherit = "env_inherit"
    Cwd = "cwd"
    Base = "base"
    Hidden = "hidden"
    Abstract = "abstract"
    ShortDesc = "short_desc"
    LongDesc = "description"
    Commands = "commands"
    StopOnError = "stop_on_error"
    Meta = "meta"
    Variables = _CommonKeys.Variables
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
    Schema = "$schema"
    Include = "include"
    UseDfltInclude = "use_default_include"
    Tasks = "tasks"
    Suppress = "suppress"
    Variables = _CommonKeys.Variables
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
        TaskKeys.EnvInherit: {"type": "boolean"},
        TaskKeys.StopOnError: {"type": "boolean"},
        TaskKeys.Hidden: {"type": "boolean"},
        TaskKeys.Abstract: {"type": "boolean"},
        TaskKeys.Variables: {"type": "object"},
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
        GlobalKeys.Schema: {
            "type": "string",
            "minLength": 1
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


class SchemaDumpOpts(object):
    ALL = "all"
    CONFIG = "config"
    TASK = "task"

    CHOICES = [ALL, CONFIG, TASK]


def dump_schema(dump_type: str) -> None:
    if dump_type == SchemaDumpOpts.CONFIG:
        print_dict(_config_file_schema)
    elif dump_type == SchemaDumpOpts.TASK:
        print_dict(_task_schema)
    elif dump_type == SchemaDumpOpts.ALL:
        _config_file_schema[GlobalKeys.Tasks] = _task_schema
        print_dict(_config_file_schema)
