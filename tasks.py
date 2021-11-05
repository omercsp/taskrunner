from typing import Union
from common import *
from config import *
from argparse import Namespace as Args
import shlex
import textwrap
import subprocess


class BaseTask(object):
    def _check_empty_setting(self, v, title) -> None:
        if v and len(v) > 0:
            return
        raise TaskException("Expanded {} for task '{}' is empty".format(title, self.name))

    def commands(self, expand: bool):
        if self.args and self.args.command:
            cmds = self.args.command
        else:
            cmds = self._task.get(TaskSchema.Keys.Commands, [])

        if expand:
            for i in range(len(cmds)):
                cmds[i] = expand_string(cmds[i], self.cmd_args, self.config.defs)
                self._check_empty_setting(cmds[i], "command #{}".format(i))
        return cmds

    def short_desc(self) -> str:
        return self._task.get(TaskSchema.Keys.ShortDesc, "")

    def long_desc(self) -> str:
        return self._task.get(TaskSchema.Keys.LongDesc, "")

    def is_abstract(self) -> bool:
        return self._task.get(TaskSchema.Keys.Abstract, False)

    def is_global(self) -> bool:
        return self._task.get(TaskSchema.Keys.Global, False)

    def stop_on_error(self) -> bool:
        if self.args and self.args.stop_on_error:
            return self.args.stop_on_error
        return self._task.get(TaskSchema.Keys.StopOnError, True)

    def cwd(self, expand: bool) -> typing.Union[str, None]:
        if self.args and self.args.cwd:
            cwd = self.args.cwd
        else:
            cwd = self._task.get(TaskSchema.Keys.Cwd, None)
        if cwd is None:
            return cwd
        if expand:
            cwd = expand_string(cwd, self.args.args, self.config.defs)
        self._check_empty_setting(self.cwd, "CWD")

    def use_shell(self):
        if self.args and self.args.shell:
            return self.args.shell
        return self._task.get(TaskSchema.Keys.Shell, False)

    def shell_path(self):
        if self.args and self.args.shell_path:
            return self.args.shell_path
        return self._task.get(TaskSchema.Keys.ShellPath, None)

    def env(self) -> typing.Union[dict, None]:
        if self.args and self.args.env:
            env = os.environ.copy()
            for e in self.args.env:
                e_name, e_value = parse_assignmet_str(e)
                env[e_name] = e_value
            return env
        else:
            return self._task.get(TaskSchema.Keys.Env, None)

    def c_image(self) -> typing.Union[str, None]:
        if self.args and self.args.c_image:
            return self.args.c_image
        self.c_settings.get(ContSchema.Keys.Image)

    def c_volumes(self, expand: bool) -> list:
        if self.args and self.args.c_volume:
            vols =  self.args.c_volume
        else:
            vols = self.c_settings.get(ContSchema.Keys.Volumes, [])
        if expand:
            for i in range(len(vols)):
                vols[i] = expand_string(vols[i], self.cmd_args, self.config.defs)
                self._check_empty_setting(vols[i], "container volume #{}".format(i))
        return vols

    def c_interactive(self) -> bool:
        if self.args and self.args.c_interactive is not None:
           return self.args.c_interactive
        return self.c_settings.get(ContSchema.Keys.Interactive, False)

    def c_tty(self) -> bool:
        if self.args and self.args.c_tty is not None:
           return self.args.c_tty
        return self.c_settings.get(ContSchema.Keys.Interactive, False)

    def c_flags(self) -> bool:
        if self.args and self.args.c_flags is not None:
           return self.args.c_flags
        return self.c_settings.get(ContSchema.Keys.Interactive, False)

    def c_tool(self) -> str:
        if self.args and self.args.c_tool is not None:
           return self.args.c_tool
        return self.c_settings.get(ContSchema.Keys.Tool, self.config.default_container_tool())

    def c_exec(self) -> bool:
        if self.args and self.args.c_exec:
            return self.args.c_exec
        return self._task.get(ContSchema.Keys.Exec, False)

    def c_rm(self) -> bool:
        if self.args and self.args.c_rm:
            return self.args.c_rm
        return self._task.get(ContSchema.Keys.Exec, False)


    def __init__(self, task: dict, name: str, config: Config, args: Args) -> None:
        super().__init__()
        self._task = task
        self.name = name
        self.config = config
        self.args = args
        self.cmd_args = args.args
        self.c_settings = self._task.get(TaskSchema.Keys.Container, {})

    def _container_execute(self, command: str) -> int:
        cmd_array = [self.c_tool()]
        cmd_array.append("exec" if self.c_exec() else "run")
        if self.cwd:
            cmd_array += ["-w", self.cwd(expand=True)]
        if self.c_interactive():
            cmd_array.append("-i")
        if self.c_tty():
            cmd_array.append("-t")
        if self.c_rm():
            cmd_array.append("--rm")

        for v in self.c_volumes(expand=True):
            cmd_array += ["-v", v]

        if self.args.c_flags():
            cmd_array += self.args.c_flags.split()

        cmd_array.append(str(self.c_image()))
        if self.use_shell():
            cmd_array += [self.shell_path(), "-c", "\"{}\"".format(command)]
        else:
            cmd_array += [command]
        p = subprocess.Popen(cmd_array, stdout=sys.stdout, stderr=sys.stderr)
        return p.wait()

    def _system_execute(self, cmd_str: str) -> int:
        if self.use_shell():
            cmd_array = [cmd_str]
        else:
            try:
                cmd_array = shlex.split(cmd_str)
            except ValueError as e:
                raise TaskException("Illegal command '{}' for task '{}' - {}".format(
                    cmd_str, self.name, e))
        try:
            p = subprocess.Popen(cmd_array, shell=self.use_shell(), executable=self.shell_path(),
                                 stdout=sys.stdout, stderr=sys.stderr, env=self.env(), 
                                 cwd=self.cwd(expand=True))
            return p.wait()
        except(OSError, FileNotFoundError) as e:
            raise TaskException("Error occured running command '{}' - {}".format(cmd_str, e))

    def execute(self) -> int:
        if self.is_abstract():
            raise TaskException("Task '{}' is abstract, and can't be ran directly")
        if self.is_global() and not self.config.setting(ConfigSchema.Keys.AllowGlobal, True):
            raise TaskException("Global tasks aren't allowed from this location")

        if not self.c_image and len(self.commands) == 0:
            print("No commands defined for task '{}'. Nothing to do.".format(self.name))
            return 0

        rc = 0
        for cmd in self.commands:
            if self.c_image:
                cmd_rc = self._container_execute(cmd)
            else:
                cmd_rc = self._system_execute(cmd)
            if cmd_rc == 0:
                continue
            if self.stop_on_error:
                return cmd_rc
            if rc == 0:
                rc = cmd_rc
        return rc

    def show_info(self, full_details: bool = False):
        PRINT_FMT = "{:<24}{:<80}"

        def print_val(title: str, value: typing.Any):
            print(PRINT_FMT.format("{}".format(title), value))

        def print_bool(title, value: bool):
            print_val(title, "Yes" if value else "No")

        def print_blob(title: str, text: str):
            if text is None or len(text) == 0:
                print(PRINT_FMT.format(title, ""))
                return
            first = True
            for line in text.split('\n'):
                for in_line in textwrap.wrap(line, width=80):
                    if first:
                        print_val(title, in_line)
                        first = False
                        continue
                    print(PRINT_FMT.format("", in_line))

        print_val("Task name:", self.name)
        print_bool("Abstract", self.abstract)
        print_bool("Global:", self.global_task)
        if full_details:
            print_val("Short description:", self.short_desc)
            if self.long_desc:
                print_blob("Description:", self.long_desc)
            print_val("Locality:", "Global" if self.global_task else "Local")

        if self.c_image:
            print_val("Container details:", "")
            if self.c_exec:
                print_val("  Execute in:", self.c_image)
            else:
                print_val("  Run image:", self.c_image)
                print_bool("  Remove:", self.c_rm)
            print_bool("  Interactive:", self.c_interactive)
            print_bool("  Allocate tty:", self.c_tty)
            if self.c_flags:
                print_blob("  Run/Exec flags:", self.c_flags)
            if len(self.c_volumes) == 1:
                print_blob("  Volume:", self.c_volumes[0])
            elif len(self.c_volumes) > 1:
                count = 0
                print(PRINT_FMT.format("  Volumes:", ""))
                for vol in self.c_volumes:
                    print_blob("     [{}]".format(count), vol)
                    count += 1

        if self.shell:
            shell_title = "Container shell:" if self.c_image else "Shell:"
            if self.shell_path:
                print_val(shell_title, self.shell_path)
            else:
                print_val(shell_title, "default (/usr/bin/sh)")

        count = 0
        if self.env:
            print(PRINT_FMT.format("Environment:", ""))
            for k, v in self.env.items():
                print_blob("     [{}]".format(count), "{}={}".format(k, v))
                count += 1

        if self.cwd:
            print_blob("Working directory:", self.cwd)
        if len(self.commands) == 0:
            print("NOTICE: No commands defined for task")
            return
        if len(self.commands) == 1:
            print_blob("Command:", self.commands[0])
            return

        print_bool("Stop on error:", self.stop_on_error)
        print_val("Commands:", "")
        count = 0
        for cmd in self.commands:
            print_blob("     [{}]".format(count), cmd)
            count += 1
