from common import *
from config import *
from argparse import Namespace as Args
import shlex
import textwrap
import subprocess


class Task(object):
    def _check_empty_setting(self, str, title):
        if len(str) > 0:
            return
        raise TaskException("Expanded {} for task '{}' is empty".format(title, self.name))

    def __init__(self, task: dict, name: str, config: Config, args: Args) -> None:
        super().__init__()
        self._task = task
        self.name = name
        self.config = config
        self.args = args
        self.short_desc = task.get(TaskSchema.Keys.ShortDesc, None)
        self.long_desc = task.get(TaskSchema.Keys.LongDesc, None)
        self.abstract = task.get(TaskSchema.Keys.Abstract, False)
        self.global_task = task["global"]
        self.cmd_args = args.args

        if args.stop_on_error:
            self.stop_on_error = args.stop_on_error
        else:
            self.stop_on_error = task.get(TaskSchema.Keys.StopOnError, True)

        if args.command:
            self.commands = args.command
        else:
            self.commands = task.get(TaskSchema.Keys.Commands, [])

        if not self.abstract:
            for i in range(len(self.commands)):
                self.commands[i] = expand_string(self.commands[i], self.cmd_args, self.config.defs)
                self._check_empty_setting(self.commands[i], "command #{}".format(i))

        if args.cwd:
            self.cwd = args.cwd
        else:
            self.cwd = task.get(TaskSchema.Keys.Cwd, None)
        if self.cwd is not None and not self.abstract:
            self.cwd = expand_string(self.cwd, self.cmd_args, config.defs)
            self._check_empty_setting(self.cwd, "CWD")

        if args.shell or task.get(TaskSchema.Keys.Shell, False):
            if args.shell_path:
                self.shell = args.shell_path
            else:
                self.shell = task.get(TaskSchema.Keys.ShellPath, config.default_shell_path())
        else:
            self.shell = None

        if args.env:
            self.env = {}
            for e in args.env:
                e_name, e_value = Task._parse_assignmet_str(e)
                self.env[e_name] = e_value
        else:
            self.env = task.get(TaskSchema.Keys.Env, None)

        c_settings = task.get(TaskSchema.Keys.Container, {})
        if args.c_image:
            self.c_image = args.c_image
        else:
            self.c_image = c_settings.get(ContSchema.Keys.Image)

        if not self.c_image:
            return

        #  Container specific settings
        if args.c_volume:
            self.c_volumes = args.c_volume
        else:
            self.c_volumes = c_settings.get(ContSchema.Keys.Volumes, [])
        if not self.abstract:
            for i in range(len(self.c_volumes)):
                self.c_volumes[i] = expand_string(self.c_volumes[i], self.cmd_args,
                                                  self.config.defs)
                self._check_empty_setting(self.c_volumes[i], "container volume #{}".format(i))

        if args.c_interactive is not None:
            self.c_interactive = args.c_interactive
        else:
            self.c_interactive = c_settings.get(ContSchema.Keys.Interactive, False)

        if args.c_tty is not None:
            self.c_tty = args.c_tty
        else:
            self.c_tty = c_settings.get(ContSchema.Keys.Tty, False)

        if args.c_flags:
            self.c_flags = args.c_flags
        else:
            self.c_flags = task.get(ContSchema.Keys.Flags, None)
        self.c_exec = args.c_exec or task.get(ContSchema.Keys.Exec, False)
        self.c_rm = task.get(ContSchema.Keys.Keep, True) if args.c_rm is None else args.c_rm

        if args.c_tool:
            self.c_tool = args.container_tool
        else:
            self.c_tool = c_settings.get(ContSchema.Keys.Tool,
                                         self.config.default_container_tool())

        if args.c_shell or c_settings.get(ContSchema.Keys.Shell, False):
            if args.c_shell_path:
                self.c_shell = args.c_shell_path
            else:
                self.c_shell = c_settings.get(ContSchema.Keys.ShellPath,
                                            self.config.default_container_shell_path())
        if args.c_cwd:
            self.c_cwd = args.c_cwd
        else:
            self.c_cwd = c_settings.get(ContSchema.Keys.Cwd, None)

    def _container_execute(self, command: str) -> int:
        cmd_array = [self.c_tool]
        cmd_array.append("exec" if self.c_exec else "run")
        if self.c_cwd:
            cmd_array += ["-w", expand_string(self.c_cwd, self.cmd_args, self.config.defs)]
        if self.c_interactive:
            cmd_array.append("-i")
        if self.c_tty:
            cmd_array.append("-t")
        if self.c_rm:
            cmd_array.append("--rm")

        for v in self.c_volumes:
            cmd_array += ["-v", v]

        if self.args.c_flags:
            cmd_array += self.args.c_flags.split()

        cmd_array.append(self.c_image)
        if self.c_shell:
            cmd_array += ["/usr/bin/sh" if self.c_shell is None else self.c_shell, "-c"]
        cmd_array += [command]
        print(" ".join(cmd_array))
        p = subprocess.Popen(cmd_array, stdout=sys.stdout, stderr=sys.stderr)
        return p.wait()

    @staticmethod
    def _parse_assignmet_str(s: str):
        parts = s.split('=', maxsplit=1)
        if len(parts) == 1:
            return s, ""
        return parts[0], str(parts[1])

    def _system_execute(self, cmd_str: str) -> int:
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

    def execute(self) -> int:
        if self.abstract:
            raise TaskException("Task '{}' is abstract, and can't be ran directly")
        if self.global_task and not self.config.setting(ConfigSchema.Keys.AllowGlobal, True):
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
        print_bool("Shell: ", self.shell is not None)
        if self.shell:
            shell_title = "Shell path:"
            if self.shell:
                print_val(shell_title, self.shell)
            else:
                print_val(shell_title, "default (/usr/bin/sh)")

        if self.c_image:
            print_val("Container details:", "")
            if self.c_exec:
                print_val("  Execute in:", self.c_image)
            else:
                print_val("  Run image:", self.c_image)
                print_bool("  Remove:", self.c_rm)
            print_bool("  Interactive:", self.c_interactive)
            print_bool("  Allocate tty:", self.c_tty)
            print_bool("  Shell: ", self.c_shell is not None)
            if self.c_shell:
                print_val( "  Shell path:", self.c_shell)
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
