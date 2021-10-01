from common import *
from config import *
from argparse import Namespace as Args
import shlex
import subprocess


class Task(object):
    def _check_empty_setting(self, str, title):
        if len(str) > 0:
            return
        raise TaskException("Expanded {} for task '{}' is empty".format(title, self.name))

    def __init__(self, task: dict, name: str, config: Config) -> None:
        super().__init__()
        self._task = task
        self.name = name
        self.config = config
        self.short_desc = task.get(TaskSchema.Keys.ShortDesc, None)
        self.long_desc = task.get(TaskSchema.Keys.LongDesc, None)
        self.hidden = task.get(TaskSchema.Keys.Hidden, False)
        self.global_task = task[TaskSchema.Keys.Global]

        self.stop_on_error = task.get(TaskSchema.Keys.StopOnError, True)
        self.commands = task.get(TaskSchema.Keys.Commands, [])
        self.cwd = task.get(TaskSchema.Keys.Cwd, None)
        self.shell = task.get(TaskSchema.Keys.Shell, False)
        self.shell_path = task.get(TaskSchema.Keys.ShellPath, config.default_shell_path())
        self.env = task.get(TaskSchema.Keys.Env, None)

        self.c_settings = task.get(TaskSchema.Keys.Container, {})
        self.c_image = self.c_settings.get(ContSchema.Keys.Image)
        self.c_volumes = self.c_settings.get(ContSchema.Keys.Volumes, [])
        self.c_interactive = self.c_settings.get(ContSchema.Keys.Interactive, False)
        self.c_tty = self.c_settings.get(ContSchema.Keys.Tty, False)
        self.c_flags = task.get(ContSchema.Keys.Flags, "")
        self.c_exec = task.get(ContSchema.Keys.Exec, False)
        self.c_rm = task.get(ContSchema.Keys.Keep, True)
        self.c_tool = self.c_settings.get(ContSchema.Keys.Tool,
                                          self.config.default_container_tool())
        self.c_shell = self.c_settings.get(ContSchema.Keys.Shell, False)
        self.c_shell_path = self.c_settings.get(ContSchema.Keys.ShellPath,
                                                self.config.default_container_shell_path())
        self.c_cwd = self.c_settings.get(ContSchema.Keys.Cwd, None)
        self.cli_args = None

    def args_update(self, args: Args) -> None:
        if args.stop_on_error:
            self.stop_on_error = args.stop_on_error
        if args.command:
            self.commands = args.command
        if args.cwd:
            self.cwd = args.cwd
        if args.shell is not None:
            self.shell = args.shell
        if args.shell_path:
            self.shell_path = args.shell_path
        if args.env:
            self.env = {}
            for e in args.env:
                e_name, e_value = parse_assignmet_str(e)
                self.env[e_name] = e_value

        if args.c_image:
            self.c_image = args.c_image
        if args.c_volume:
            self.c_volumes = args.c_volume
        if args.c_interactive is not None:
            self.c_interactive = args.c_interactive
        if args.c_tty is not None:
            self.c_tty = args.c_tty
        if args.c_flags:
            self.c_flags = args.c_flags
        if args.c_exec:
            self.c_exec = args.c_exec
        if args.c_rm:
            self.c_rm = args.c_rm
        if args.c_tool:
            self.c_tool = args.container_tool
        if args.c_shell is not None:
            self.c_shell = args.c_shell
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
        cmd_array = [self.c_tool]
        cmd_array.append("exec" if self.c_exec else "run")
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
        print(cmd_array)
        return cmd_array

    def _run_cmd(self, cmd: list, cmd_str: str) -> int:
        try:
            if self.env is None:
                penv = None
            else:
                penv = os.environ.copy()
                penv.update(self.env)
            p = subprocess.Popen(cmd, shell=self.shell, executable=self.shell_path,
                                 stdout=sys.stdout, stderr=sys.stderr, env=penv, cwd=self.cwd)
            return p.wait()

        except (OSError, FileNotFoundError) as e:
            raise TaskException("Error occured running command '{}' - {}".format(cmd_str, e))

    def run(self) -> int:
        if self.global_task and not self.config.setting(ConfigSchema.Keys.AllowGlobal, True):
            raise TaskException("Global tasks aren't allowed from this location")

        cmds = self.commands
        if len(cmds) == 0:
            if self.c_image:
                return self._run_cmd(self._container_cmd_arr(None), "<CONTAINER_DEFAULT>")
            print("No commands defined for task '{}'. Nothing to do.".format(self.name))
            return 0

        rc = 0
        for cmd in self.commands:
            cmd = self._expand(cmd)
            if self.cli_args:
                cmd += " " + self.cli_args
            cmd_arr = self._container_cmd_arr(cmd) if self.c_image else self._simple_cmd_arr(cmd)
            cmd_rc = self._run_cmd(cmd_arr, cmd)
            if cmd_rc == 0:
                continue
            if self.stop_on_error:
                return cmd_rc
            if rc == 0:
                rc = cmd_rc
        return rc
