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
        self.abstract = task.get(TaskSchema.Keys.Abstract, False)
        self.global_task = task[TaskSchema.Keys.Global]

        self.stop_on_error = task.get(TaskSchema.Keys.StopOnError, True)
        self.commands = task.get(TaskSchema.Keys.Commands, [])
        self.cwd = task.get(TaskSchema.Keys.Cwd, None)
        if task.get(TaskSchema.Keys.Shell, False):
            self.shell = task.get(TaskSchema.Keys.ShellPath, config.default_shell_path())
        else:
            self.shell = None
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

        if self.c_settings.get(ContSchema.Keys.Shell, False):
            self.c_shell = self.c_settings.get(ContSchema.Keys.ShellPath,
                                               self.config.default_container_shell_path())
        else:
            self.c_shell = None
        self.c_cwd = self.c_settings.get(ContSchema.Keys.Cwd, None)
        self.cli_args = []

    def args_update(self, args: Args) -> None:
        if args.stop_on_error:
            self.stop_on_error = args.stop_on_error
        if args.command:
            self.commands = args.command
        if args.cwd:
            self.cwd = args.cwd
        if args.shell:
            self.shell = args.shell_path if args.shell_path else \
                self._task.get(TaskSchema.Keys.ShellPath, self.config.default_shell_path())
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
        if args.c_shell:
            if args.c_shell_path:
                self.c_shell = args.c_shell_path
            else:
                self.c_shell = self.c_settings.get(ContSchema.Keys.ShellPath,
                                                   self.config.default_container_shell_path())
        if args.c_cwd:
            self.c_cwd = args.c_cwd
        if args.arg:
            self.cli_args = args.arg


    def _expand(self, s: str) -> str:
        return expand_string(s, self.cli_args, self.config.defs)

    def _container_run(self, command: str) -> int:
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
        if self.c_shell:
            cmd_array += ["/usr/bin/sh" if self.c_shell is None else self.c_shell, "-c"]
        cmd_array += [command]
        print(cmd_array)
        p = subprocess.Popen(cmd_array, stdout=sys.stdout, stderr=sys.stderr)
        return p.wait()

    def _system_run(self, cmd_str: str) -> int:
        if self.shell:
            cmd_array = [cmd_str]
        else:
            try:
                cmd_array = shlex.split(cmd_str)
            except ValueError as e:
                raise TaskException("Illegal command '{}' for task '{}' - {}".format(
                    cmd_str, self.name, e))
        try:
            if self.env is None:
                penv = None
            else:
                penv = os.environ.copy()
                penv.update(self.env)
            p = subprocess.Popen(cmd_array, shell=self.shell is not None, executable=self.shell,
                                 stdout=sys.stdout, stderr=sys.stderr, env=penv, cwd=self.cwd)
            return p.wait()

        except (OSError, FileNotFoundError) as e:
            raise TaskException("Error occured running command '{}' - {}".format(cmd_str, e))

    def run(self) -> int:
        if self.abstract:
            raise TaskException("Task '{}' is abstract, and can't be ran directly")
        if self.global_task and not self.config.setting(ConfigSchema.Keys.AllowGlobal, True):
            raise TaskException("Global tasks aren't allowed from this location")

        if not self.c_image and len(self.commands) == 0:
            print("No commands defined for task '{}'. Nothing to do.".format(self.name))
            return 0

        rc = 0
        for cmd in self.commands:
            cmd = self._expand(cmd)
            if self.c_image:
                cmd_rc = self._container_run(cmd)
            else:
                cmd_rc = self._system_run(cmd)
            if cmd_rc == 0:
                continue
            if self.stop_on_error:
                return cmd_rc
            if rc == 0:
                rc = cmd_rc
        return rc

