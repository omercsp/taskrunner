from common import *
from config import *
from argparse import Namespace as Args
import shlex
import textwrap
import subprocess


class Task(object):
    def __init__(self, task: dict, name: str, config: Config, args: Args) -> None:
        super().__init__()
        self._task = task
        self.name = name
        self.config = config
        self.args = args
        self.short_desc = task.get(TaskKeys.SHORT_DESC, None)
        self.long_desc = task.get(TaskKeys.LONG_DESC, None)

        if args.stop_on_error:
            self.stop_on_error = args.stop_on_error
        else:
            self.stop_on_error = task.get(TaskKeys.STOP_ON_ERROR, True)

        if args.command:
            self.commands = args.command
        elif args.command_append:
            self.commands += args.append_command
        else:
            self.commands = task.get(TaskKeys.COMMANDS, [])

        if args.cwd:
            self.cwd = args.cwd
        else:
            self.cwd = task.get(TaskKeys.CWD, None)

        if args.shell:
            self.shell = args.shell
        else:
            self.shell = task.get(TaskKeys.SHELL, False)

        if self.shell:
            if args.shell_path:
                self.shell_path = args.shell_path
            else:
                self.shell_path = task.get(TaskKeys.SHELL_PATH, config.default_shell_path())
        else:
            self.shell_path = None

        cli_env = []
        if args.env:
            cli_env = args.env
            self.env = {}
        else:
            self.env = task.get(TaskKeys.ENV, {})
            if args.env_append:
                cli_env = args.env_append

        for e in cli_env:
            e_name, e_value = Task._parse_assignmet_str(e)
            self.env[e_name] = e_value

        container = task.get(TaskKeys.CONTAINER, {})
        if args.image:
            self.image = args.image
        else:
            self.image = container.get(TaskKeys.Container.IMAGE)

        if not self.image:
            return

        #  Container specific settings
        if args.volumes:
            self.volumes = args.volumes
        else:
            self.volumes = container.get(TaskKeys.Container.VOLUMES, [])
            if args.volumes_append:
                self.volumes += args.volumes_append

        if args.interactive is not None:
            self.interactive = args.interactive
        else:
            self.interactive = task.get(TaskKeys.Container.INTERACTIVE, False)

        if args.tty is not None:
            self.tty = args.tty
        else:
            self.tty = task.get(TaskKeys.Container.TTY, False)

        if args.container_tool:
            self.container_tool = args.container_tool
        else:
            self.container_tool = container.get(TaskKeys.Container.CONTAINER_TOOL,
                                                self.config.default_container_tool())

    def _container_execute(self, command: str) -> int:
        cmd_array = [self.container_tool, "run", "--rm"]
        if self.cwd:
            cmd_array += ["-w", self.cwd]
        if self.interactive:
            cmd_array.append("-i")
        if self.tty:
            cmd_array.append("-t")

        for v in self.volumes:
            cmd_array += ["-v", expand_string(v, self.config.defs)]

        if self.args.container_flags:
            cmd_array += self.args.container_flags.split()

        cmd_array.append(self.image)
        if self.shell:
            shell = "/usr/bin/sh" if self.shell_path is None else self.shell_path
            command = "\"{}\"".format(command)
            cmd_array += [shell, "-c", "\"{}\"".format(command)]
        else:
            cmd_array += [command]
        print(cmd_array)
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
                #  penv = os.environ.copy()
                penv = {}
                penv.update(self.env)
            p = subprocess.Popen(cmd_array, shell=self.shell, executable=self.shell_path,
                                 stdout=sys.stdout, stderr=sys.stderr, env=penv, cwd=self.cwd)
            return p.wait()

        except (OSError, FileNotFoundError) as e:
            raise TaskException("Error occured running command '{}' - {}".format(cmd_str, e))

    def execute(self) -> int:
        if not self.image and len(self.commands) == 0:
            print("No commands defined for task '{}'. Nothing to do.".format(self.name))
            return 0

        rc = 0
        for cmd in self.commands:
            cmd_str = expand_string(cmd, self.config.defs)
            if self.image:
                cmd_rc = self._container_execute(cmd_str)
            else:
                cmd_rc = self._system_execute(cmd_str)
            if cmd_rc == 0:
                continue
            if self.stop_on_error:
                return cmd_rc
            if rc == 0:
                rc = cmd_rc
        return rc

    def show_info(self):
        PRINT_FMT = "{:<24}{:<80}"

        def print_val(title: str, value: typing.Any):
            print(PRINT_FMT.format("{}".format(title), value))

        def print_bool(title, value: bool):
            print_val(title, "Yes" if value else "No")

        def print_blob(title: str, text: str):
            if text is None:
                text = ""
            first = True
            for line in text.split('\n'):
                for in_line in textwrap.wrap(line, width=80):
                    if first:
                        print_val(title, in_line)
                        first = False
                        continue
                    print(PRINT_FMT.format("", in_line))

        print(PRINT_FMT.format("Task name:", self.name))
        print_val("Short description:", self.short_desc)
        if self.long_desc:
            print_blob("Description:", self.long_desc)

        if self.image:
            print_val("Image:", self.image)
            print_bool("Interactive container:", self.interactive)
            print_bool("Container TTY:", self.tty)
            if self.args.container_flags:
                print_blob("Container flags:", self.args.container_flags)
            if len(self.volumes) == 1:
                print_blob("Volume:", self.volumes[0])
            elif len(self.volumes) > 1:
                count = 0
                print(PRINT_FMT.format("Volumes:", ""))
                for vol in self.volumes:
                    print_blob("     [{}]".format(count), vol)
                    count += 1

        if self.shell:
            if self.shell_path:
                print_val("Shell:", self.shell_path)
            else:
                print_val("Shell:", "default (/usr/bin/sh)")
        print_bool("Stop on error:", self.stop_on_error)

        count = 0
        if self.env:
            print(PRINT_FMT.format("Environment:", ""))
            for k, v in self.env.items():
                print_blob("     [{}]".format(count), "{}={}".format(k, v))
                count += 1

        if len(self.commands) == 0:
            print("NOTICE: No commands defined for task")
            return
        if len(self.commands) == 1:
            print_blob("Command:", expand_string(self.commands[0], self.config.defs))
            return

        print(PRINT_FMT.format("Commands:", ""))
        count = 0
        for cmd_str in self.commands:
            print_blob("     [{}]".format(count), expand_string(cmd_str, self.config.defs))
            count += 1
