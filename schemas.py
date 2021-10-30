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
        },
        "additionalProperties": False,
        "required": [Keys.Image]
    }


class TaskSchema(object):
    class Keys(object):
        Include = "include"
        ShortDesc = "short_desc"
        LongDesc = "description"
        Commands = "commands"
        Shell = "shell"
        ShellPath = "shell_path"
        StopOnError = "stop_on_error"
        Env = "env"
        Cwd = "cwd"
        Container = "container"
        Abstract = "abstract"
        Global = "global"
    schema = {
        "type": "object",
        "properties": {
            Keys.Include: {
                "type": "array",
                "items": {"type": "string", "minLength": 1}
            },
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
            Keys.Container:  {"type": "string", "maxLength": 64},
            Keys.Abstract: {"type": "boolean"},
            Keys.Global: {"type": "boolean"},
        },
        "additionalProperties": False
    }


class ConfigSchema(object):
    class Keys(object):
        Version = "version"
        Tasks = "tasks"
        Definitions = "definitions"
        DfltTask = "default_task"
        DfltShellPath = "defult_shell_path"
        DfltContainerTool = "default_container_tool"
        Containers = "containers"
    schema = {
        "type": "object",
        "properties": {
            Keys.Version: {
                "type": "object",
                "properties": {
                    "major": {"type": "number", "minValue": 0},
                    "minor": {"type": "number", "minValue": 1}
                }
            },
            Keys.Tasks: {"type": "object"},
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
            Keys.DfltContainerTool: {"type": "string", "minLength": 1}
        },
        "required": [Keys.Version],
        "additionalProperties": False
    }
