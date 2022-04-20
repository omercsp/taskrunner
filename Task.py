from config import *
from argparse import Namespace as Args
from schemas import Schema
import shlex
import subprocess
import signal


class Task(object):
    def _check_empty_setting(self, s, title):
        if len(s) > 0:
            return
        raise TaskException("Expanded {} for task '{}' is empty".format(title, self.name))

    def __init__(self, name: str, config: Config) -> None:
        super().__init__()
        info("Initializing task '{}'", name)
        task_descriptor = config.get_task_desc(name, True)
        self.name = name
        self.config = config
        self.short_desc = task_descriptor.get(Schema.Keys.Task.ShortDesc, None)
        self.long_desc = task_descriptor.get(Schema.Keys.Task.LongDesc, None)
        self.hidden = task_descriptor.get(Schema.Keys.Task.Hidden, False)

        self.stop_on_error = task_descriptor.get(Schema.Keys.Task.StopOnError, True)
        self.commands = task_descriptor.get(Schema.Keys.Task.Commands, [])
        self.cwd = task_descriptor.get(Schema.Keys.Task.Cwd, None)
        self.shell = task_descriptor.get(Schema.Keys.Task.Shell, False)
        self.shell_path = task_descriptor.get(
            Schema.Keys.Task.ShellPath, config.default_shell_path())
        self.env = task_descriptor.get(Schema.Keys.Task.Env, None)

        self.c_image = task_descriptor.get(Schema.Keys.Task.CImage, None)
        self.c_volumes = task_descriptor.get(Schema.Keys.Task.CVolumes, [])
        self.c_interactive = task_descriptor.get(Schema.Keys.Task.CInteractive, False)
        self.c_tty = task_descriptor.get(Schema.Keys.Task.CTty, False)
        self.c_flags = task_descriptor.get(Schema.Keys.Task.CFlags, "")
        self.c_exec = task_descriptor.get(Schema.Keys.Task.CExec, False)
        self.c_rm = task_descriptor.get(Schema.Keys.Task.CRemove, True)
        self.c_tool = task_descriptor.get(Schema.Keys.Task.CTool,
                                          self.config.default_container_tool())
        self.c_shell = task_descriptor.get(Schema.Keys.Task.CShell, False)
        self.c_shell_path = task_descriptor.get(Schema.Keys.Task.CShellPath,
                                                self.config.default_container_shell_path())
        self.c_cwd = task_descriptor.get(Schema.Keys.Task.CCwd, None)
        self.c_env = task_descriptor.get(Schema.Keys.Task.CEnv, {})
        self.c_sudo = task_descriptor.get(Schema.Keys.Task.CSudo, False)

        self.expanded = False

    def args_update(self, args: Args) -> None:
        if args.stop_on_error:
            self.stop_on_error = args.stop_on_error
        if args.command:
            self.commands = args.command
        if args.cwd:
            self.cwd = args.cwd
        if args.shell:
            self.shell = (args.shell == TASK_YES_TOKEN)
        if args.shell_path:
            self.shell_path = args.shell_path
        if args.env:
            self.env = {}
            for e in args.env:
                e_name, e_value = parse_assignment_str(e)
                self.env[e_name] = e_value

        if args.c_image:
            self.c_image = args.c_image
        if args.c_volume:
            self.c_volumes = args.c_volume
        if args.c_interactive:
            self.c_interactive = (args.c_interactive == TASK_YES_TOKEN)
        if args.c_tty:
            self.c_tty = (args.c_tty == TASK_YES_TOKEN)
        if args.c_flags:
            self.c_flags = args.c_flags
        if args.c_exec:
            self.c_exec = args.c_exec
        if args.c_rm:
            self.c_rm = (args.c_rm == TASK_YES_TOKEN)
        if args.c_tool:
            self.c_tool = args.container_tool
        if args.c_shell:
            self.c_shell = (args.c_shell == TASK_YES_TOKEN)
        if args.c_shell_path:
            self.c_shell_path = args.c_shell_path
        if args.c_cwd:
            self.c_cwd = args.c_cwd
        if args.c_env:
            self.c_env = {}
            for e in args.c_env:
                e_name, e_value = parse_assignment_str(e)
                self.c_env[e_name] = e_value

    def expand_args(self, expander: StringVarExpander) -> None:
        if self.expanded:
            warn("Task '{}' is already expanded", self.name)
            return
        info("Expanding task '{}'".format(self.name))
        self.expanded
        if self.env is not None:
            self.env = {expander(k): expander(v) for k, v in self.env.items()}
            for k, v in self.env.items():
                info("Environment variable will be set as '{}={}'", k, v)
        if self.cwd:
            self.cwd = expander(self.cwd)
        self.commands = [expander(c) for c in self.commands]

        if self.c_cwd:
            self.c_cwd = expander(self.cwd)
        if self.c_image:
            self.c_image = expander(self.c_image)
        self.c_volumes = ["-v {}".format(v) for v in self.c_volumes]
        self.c_env = {expander(k): expander(v) for k, v in self.c_env.items()}


    def _simple_cmd_arr(self, cmd) -> list:
        info("Preparing simple command")
        if self.shell:
            return [cmd]
        try:
            return shlex.split(cmd)
        except ValueError as e:
            raise TaskException("Illegal command '{}' for task '{}' - {}".format(cmd, self.name, e))

    def _container_cmd_arr(self, cmd) -> list:
        info("Preparing container command")
        cmd_array = ["sudo", self.c_tool] if self.c_sudo else [self.c_tool]
        cmd_array.append("exec" if self.c_exec else "run")
        if self.c_cwd:
            cmd_array += ["-w", self.c_cwd]
        if self.c_interactive:
            cmd_array.append("-i")
        if self.c_tty:
            cmd_array.append("-t")
        if not self.c_exec:
            if self.c_rm:
                cmd_array.append("--rm")
            for v in self.c_volumes:
                cmd_array += ["-v", v]

        for k, v in self.c_env.items():
            cmd_array += ["-e", "{}={}".format(k, v)]
            info("Setting container environment variable will '{}={}'", k, v)

        cmd_array += self.c_flags.split()

        cmd_array.append(self.c_image)
        if self.c_shell and cmd is not None:
            cmd_array += [self.c_shell_path, "-c"]
        if cmd:
            cmd_array += [cmd]
        info("Command is {}", cmd_array)
        return cmd_array

    def _run_cmd(self, cmd: list, cmd_str: str) -> int:
        info("Running command (joined):")
        raw_msg(cmd_str)
        p = None
        try:
            p = subprocess.Popen(cmd, shell=self.shell, executable=self.shell_path, env=self.env,
                                 cwd=self.cwd)
            return p.wait()

        except (OSError, FileNotFoundError) as e:
            raise TaskException("Error occurred running command '{}' - {}".format(cmd_str, e))
        except KeyboardInterrupt:
            if p:
                p.send_signal(signal.SIGINT)
                p.wait()
            raise TaskException("User interrupt")

    def run(self) -> int:
        if self.expanded:
            raise TaskException("Task must be expanded before run")  # Should never happen
        if self.cwd:
            info("Working directory will be set to '{}'", self.cwd)
        else:
            info("No working directory will be set")

        if len(self.commands) == 0:
            if self.c_image:
                info("Running container's default command")
                return self._run_cmd(self._container_cmd_arr(None), "<CONTAINER_DEFAULT>")
            print("No commands defined for task '{}'. Nothing to do.".format(self.name))
            return 0

        rc = 0
        for cmd in self.commands:
            info("Command is '{}'", cmd)
            cmd_arr = self._container_cmd_arr(cmd) if self.c_image else self._simple_cmd_arr(cmd)
            cmd_rc = self._run_cmd(cmd_arr, cmd)
            if cmd_rc == 0:
                continue
            info("Command had failed")
            if self.stop_on_error:
                info("Stopping of first error")
                return cmd_rc
            if rc == 0:
                rc = cmd_rc
        return rc
