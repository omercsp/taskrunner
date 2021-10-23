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

        raw_envs = []
        if args.env:
            raw_envs = args.env
            self.env = {}
        elif args.env_append:
            raw_envs = args.env_append
            self.env = task.get(TaskKeys.ENV, {})
        else:
            self.env = None
        for e in raw_envs:
            e_name, e_value = Task._parse_env_string(e)
            self.env[e_name] = e_value
        if args.image:
            self.imaeg = args.image
        else:
            self.image = task.get(TaskKeys.IMAGE, None)

    def _gen_command_array(self, command: str, shell: bool) -> list:
        #  When using shell, pass the command  'as is'
        if shell:
            return [command]
        try:
            return shlex.split(command)
        except ValueError as e:
            raise TaskException("Illegal command '{}' for task '{}' - {}".format(command, self.name, e))


    def _active_task_name(self, config: Config, args) -> str:
        task_name = config.default_task_name() if args.task is None else args.task
        if task_name is None:
            raise TaskException("No main task name was given")
        return task_name


    @staticmethod
    def _parse_env_string(s: str):
        parts = s.split('=', maxsplit=1)
        if len(parts) == 1:
            return s, ""
        return parts[0], str(parts[1])


    def _exec_default_command(self) -> int:
        if len(self.commands) == 0:
            print("No commands defined for task '{}'. Nothing to do.".format(self.name))
            return 0

        rc = 0
        for cmd_str in self.commands:
            cmd_str = expand_string(cmd_str, self.config.defs)
            cmd_array = self._gen_command_array(cmd_str, self.shell)
            try:
                if self.env is None:
                    penv = None
                else:
                    penv = os.environ.copy()
                    penv.update(self.env)
                p = subprocess.Popen(cmd_array, shell=self.shell, executable=self.shell_path,
                                     stdout=sys.stdout, stderr=sys.stderr, env=penv)
                cmd_rc = p.wait()
            except (OSError, FileNotFoundError) as e:
                raise TaskException("Error occured running command '{}' - {}".format(cmd_str, e))
            if cmd_rc == 0:
                continue
            if self.stop_on_error:
                return cmd_rc
            if rc == 0:
                rc = cmd_rc
        return rc

    def _exec_image_command(self) -> int:
        return 0

    def execute(self) -> int:
        if self.image:
            return self._exec_image_command()
        else:
            return self._exec_default_command()

    def show_info(self):
        PRINT_FMT = "{:<24}{:<80}"

        def print_val(title: str, value: typing.Any):
            print(PRINT_FMT.format("{}".format(title), value))

        def print_bool(title, value: bool):
            print_val(title, "Yes" if value else "No")

        def print_blob(title:str , text: str):
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
        if self.shell:
            if self.shell_path:
                print_val("Shell:", self.shell_path)
            else:
                print_val("Shell:", "default (/usr/bin/sh)")
        print_bool("Stop on error:", self.stop_on_error)
        if self.image:
            print_val("Image:", self.image)

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
            print_blob("Command:", self.commands[0])
            return

        print(PRINT_FMT.format("Commands:", ""))
        count = 0
        for cmd_str in self.commands:
            print_blob("     [{}]".format(count), expand_string(cmd_str, self.config.defs))
            count += 1
