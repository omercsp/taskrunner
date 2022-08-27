# Global Configuration settings
* `include` - List of configuration files to be included by this file. They are read in order, one by one. Overlapped settings are overridden (type: array of strings, empty default value).
* `use_default_include` - Determine weather to include the default configuration file at `${HOME}/.config/tasks.json` if it exists (type: boolean, default value: `false`)
* `version` - Configuration file schema version. Used for validation when the configuration file is read (required, type: object, empty default value)
* `tasks` - List of tasks. See [tasks](#tasks-settings) section for details (type: object, empty default value).
* `supress` - List of tasks that are suppressed in this context. This is only useful when some unwonted tasks are included by this configuration file that the user want to 'turn off' (type: array of strings, empty default value).
* `variables` - Set dictionary of variables for tasks. Each `"key": "val"` in the dictionary sets a variable named `key`, which can be referred to by using `{{key}}` in various tasks settings (type: object, empty default value)
* `default_task` - Name of default task to run if no task name is given (type: string, empty default value).
* `default_shell_path` - Default path for for commands that uses `shell` but don't define their own shell path (type string, default value: `/usr/bin/sh`)
* `default_container_shell_path` - Same as as `default_shell_path`, but for container tasks, that is - with which shell command to wrap the container command with (type string, default value: `/usr/bin/sh`).
* `default_container_tool` - Which tool to use when running container based tasks. This tool should be compatible for some `docker` flags like (`-w` for working directories, `-v` for volumes, etc.). `podman` is tested to compatible (type: string, default value: `/usr/bin/docker`).

# Tasks Settings
* `short_desc` - A short description of the task. This setting is shown when listing the tasks. It has a max size of 75 characters. For a more detailed documentation of the task, use `description` (type: string, empty default value).
* `description` - A blob describing the task. No word limit. Displayed when using `task info` (type: string, empty default value).
* `commands` - List of commands to run by the task. Each command is ran in turn. This setting can be absent or empty, but doesn't make much sense unless used for inheritance (see, `base` setting) (type: list of strings, empty default value).
* `stop_on_error` - Determines weather to stop on first error in case of multiple commands are set for the task (type: Boolean, default value: `false`)
* `cwd` - Sets the working directory for commands to run (type: string. If not set, the current working directory is use as the commands working directory as well).
* `env` - Dictionary of `"key": "val"`. Each pair will define an environment variable to set when running the task's commands (type: object, empty default value).
* `env_inherit` - Sets weather the task environment variables are inherited from the system set of variables or not. (type: boolean, default value: `true`)
* `shell` - Sets if the commands in this tasks are ran with a wrapping shell. In general this should be not used unless the task's commands require shell semantics like redirection. (type: Boolean, default value: `false`)
* `shell_path` - Path for shell to use if `shell` is set to true (type: string, default value: the global `default_shell_path` value, which is `/usr/bin/sh` if unmodified)
* `hidden` - Hides task from being listed by default. Hidden tasks can still be listed using `--all` flag. (type: Boolean, default value: `false`).
* `abstract` - Abastrct tasks are not allowed to be run. This setting is useful when there's a need to mark task as a base task, while preventing it from being wrongfuly ran. Abstract tasks are implictly hidden. (type: Boolean, default value: `false`).
* `base` - An optional task name to inherit from. Any current task settings override inherited settings (type: string, empty default value).
* `meta` - A dictionary for the user own use. TR does not refer to values in this object (type: object, empty default value).
* `variables` - A dictionary for task sepecific variables. These variables are not exposed to other tasks with the exception of tasks that inherit this task. Task variables override global variables with the same name.

## Task Container Settings
* `c_image` - Image name for container tool to use. Unless set, the task isn't ran inside a container. If `c_exec` is set to `true`, `c_image` *doesn't* refer to an image, but to container that is expected to be running before the task is executed. See `c_exec` setting for more details (type: string, empty default value).
* `c_container_tool` - Container tool to use when running the task command (type: string, default value is set according to the `default_container_tool` which is `/usr/bin/docker` by default).
* `c_volumes` - A list of volumes to pass to the container command. Each entry in the list should be in the format of `HOST_DIR:CONTAINER_DIR`. When running, each such entry is translated `-v HOST_DIR:CONTAINER_DIR`. Ignored if `c_exec` is set to `true` (type: object, empty default value).
* `c_interactive` - Sets weather the container is ran in an interactive mode using `-i` flag (type: boolean, default value: `false`).
* `c_tty` - Sets weather the container is ran with an allocated terminal using the `-t` flag (type: boolean, default value: `false`).
* `c_flags` - Additional flags to pass to the container tool when executing commands. These flags are passe 'as is' (type: string, empty default value).
* `c_exec` - Sets weather the task should used an already running container instead of running a new image. Setting this to `true` means the container tool will use `exec` command instead of `run` and the value of `c_image` is used for the running container reference (name or hash). (type: boolean, default value: `false`).
* `c_remove` - Sets weather container is removed after executing each command. Ignored if `c_exec` is set to `true` (type: boolean, default value: `true`).
* `c_sudo` - Runs the container command as root. Usually this isn't a good idea, but occasionally there's a need. Setting this to true will prefix the container tool with `sudo` (type: boolean, default value: `false`).
* `c_shell` - Set weather to prefix the running command running in the container with `<SHELL> -c` (and surround it with a brackets). By default the shell used is `/usr/bin/sh`, modifiable by setting `c_shell_path`. (type: boolean, default: false)
* `c_shell_path` - Set the shell to use if `c_shell` is set (type: string, empty default value).
* `c_env` - Dictionary of `"key": "val"`. Each pair will define an environment variable for the container using `-e` flags (type: object, empty default value).
* `c_cwd` - Sets the working directory for the command in a container. Translates into `-w <CWD>` flag. If not set, the container default working directory is used (type: string, empty default value).
