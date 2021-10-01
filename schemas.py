class CommonKeys(object):
    Shell = "shell"
    ShellPath = "shell_path"
    Env = "env"
    Cwd = "cwd"


class ContSchema(object):
    class Keys(object):
        Image = "image"
        Tool = "container_tool"
        Volumes = "volumes"
        Interactive = "interactive"
        Tty = "tty"
        Flags = "flags"
        Exec = "exec"
        Keep = "keep"
        Shell = CommonKeys.Shell
        ShellPath = CommonKeys.ShellPath
        Env = CommonKeys.Env
        Cwd = CommonKeys.Cwd

    schema = {
        "type": "object",
        "properties": {
            Keys.Image: {"type": "string", "maxLength": 64},
            Keys.Tool: {"type": "string"},
            Keys.Volumes: {
                "type": "array",
                "items": {"type": "string"}
            },
            Keys.Interactive: {"type": "boolean"},
            Keys.Tty: {"type": "boolean"},
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
        "additionalProperties": False,
        "required": [Keys.Image]
    }


class TaskSchema(object):
    class Keys(object):
        Include = "include"
        Shell = CommonKeys.Shell
        ShellPath = CommonKeys.ShellPath
        Env = CommonKeys.Env
        Cwd = CommonKeys.Cwd
        ShortDesc = "short_desc"
        LongDesc = "description"
        Commands = "commands"
        StopOnError = "stop_on_error"
        Container = "container"
        Abstract = "abstract"
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
            Keys.Container: ContSchema.schema,
            Keys.Abstract: {"type": "boolean"},
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
        Definitions = "definitions"
        DfltTask = "default_task"
        DfltShellPath = "defult_shell_path"
        DfltContainerShellPath = "defult_container_shell_path"
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
            Keys.Tasks: {"type": "object"},
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
