from config import *
from argparse import Namespace as Args
import shlex
import subprocess
import signal


class Task(object):
    def _check_empty_setting(self, s, title):
        if len(s) > 0:
            return
        raise TaskException("Expanded {} for task '{}' is empty".format(title, self.name))

    def __init__(self, name: str, glbl: bool, config: Config) -> None:
        super().__init__()
        task_descriptor = config.task_descriptor(name, force_global=glbl)
        self.name = name
        self.config = config
        self.short_desc = task_descriptor.get(TaskSchema.Keys.ShortDesc, None)
        self.long_desc = task_descriptor.get(TaskSchema.Keys.LongDesc, None)
        self.hidden = task_descriptor.get(TaskSchema.Keys.Hidden, False)
        self.global_task = task_descriptor[TaskSchema.Keys.Global]

        self.stop_on_error = task_descriptor.get(TaskSchema.Keys.StopOnError, True)
        self.commands = task_descriptor.get(TaskSchema.Keys.Commands, [])
        self.cwd = task_descriptor.get(TaskSchema.Keys.Cwd, None)
        self.shell = task_descriptor.get(TaskSchema.Keys.Shell, False)
        self.shell_path = task_descriptor.get(
            TaskSchema.Keys.ShellPath, config.default_shell_path())
        self.env = task_descriptor.get(TaskSchema.Keys.Env, None)

        self.c_name = task_descriptor.get(TaskSchema.Keys.Container, None)
        if self.c_name:
            self.expected_container = True
            c_settings = config.container_descriptor(self.c_name)
        else:
            self.expected_container = False
            c_settings = {}

        self.c_image = c_settings.get(ContSchema.Keys.Image, None)
        self.c_volumes = c_settings.get(ContSchema.Keys.Volumes, [])
        self.c_interactive = c_settings.get(ContSchema.Keys.Interactive, False)
        self.c_tty = c_settings.get(ContSchema.Keys.Tty, False)
        self.c_flags = c_settings.get(ContSchema.Keys.Flags, "")
        self.c_exec = c_settings.get(ContSchema.Keys.Exec, False)
        self.c_rm = c_settings.get(ContSchema.Keys.Remove, True)
        self.c_tool = c_settings.get(ContSchema.Keys.Tool,
                                     self.config.default_container_tool())
        self.c_shell = c_settings.get(ContSchema.Keys.Shell, False)
        self.c_shell_path = c_settings.get(ContSchema.Keys.ShellPath,
                                           self.config.default_container_shell_path())
        self.c_cwd = c_settings.get(ContSchema.Keys.Cwd, None)
        self.cli_args = None

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
        if args.args:
            self.cli_args = args.args

    def _expand(self, s: str) -> str:
        return expand_string(s, self.config.defs)

    def _simple_cmd_arr(self, cmd) -> list:
        if self.shell:
            return [cmd]
        try:
            return shlex.split(cmd)
        except ValueError as e:
            raise TaskException("Illegal command '{}' for task '{}' - {}".format(cmd, self.name, e))

    def _container_cmd_arr(self, cmd) -> list:
        cmd_array = [self.c_tool, "exec" if self.c_exec else "run"]
        if self.c_cwd:
            cmd_array += ["-w", self._expand(self.c_cwd)]
        if self.c_interactive:
            cmd_array.append("-i")
        if self.c_tty:
            cmd_array.append("-t")
        if self.c_rm:
            cmd_array.append("--rm")

        for v in self.c_volumes:
            cmd_array += ["-v", self._expand(v)]

        cmd_array += self.c_flags.split()

        cmd_array.append(self.c_image)
        if self.c_shell and cmd is not None:
            cmd_array += [self.c_shell_path, "-c"]
        if cmd:
            cmd_array += [cmd]
        return cmd_array

    def _run_cmd(self, cmd: list, cmd_str: str, env: typing.Union[dict, None], cwd) -> int:
        p = None
        try:
            p = subprocess.Popen(cmd, shell=self.shell, executable=self.shell_path, env=env,
                                 cwd=cwd)
            return p.wait()

        except (OSError, FileNotFoundError) as e:
            raise TaskException("Error occurred running command '{}' - {}".format(cmd_str, e))
        except KeyboardInterrupt:
            if p:
                p.send_signal(signal.SIGINT)
                p.wait()
            raise TaskException("User interrupt")

    def run(self) -> int:
        if self.global_task and not self.config.setting(ConfigSchema.Keys.AllowGlobal, True):
            raise TaskException("Global tasks aren't allowed from this location")

        if self.expected_container and self.c_image is None:
            raise TaskException("Task included a container reference, but now image was defined")

        if self.env is None:
            penv = None
        else:
            penv = os.environ.copy()
            penv.update(self.env)
        cwd = self._expand(self.cwd) if self.cwd else None

        cmds = self.commands
        if len(cmds) == 0:
            if self.c_image:
                return self._run_cmd(self._container_cmd_arr(None), "<CONTAINER_DEFAULT>", penv,
                                     cwd)
            print("No commands defined for task '{}'. Nothing to do.".format(self.name))
            return 0

        rc = 0
        for cmd in self.commands:
            cmd = self._expand(cmd)
            if self.cli_args:
                cmd += " " + self.cli_args
            cmd_arr = self._container_cmd_arr(cmd) if self.c_image else self._simple_cmd_arr(cmd)
            cmd_rc = self._run_cmd(cmd_arr, cmd, penv, cwd)
            if cmd_rc == 0:
                continue
            if self.stop_on_error:
                return cmd_rc
            if rc == 0:
                rc = cmd_rc
        return rc
