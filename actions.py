from common import *
from config import *
from argparse import Namespace as Args
import shlex
import textwrap
import subprocess


def _gen_command_array(command: str, shell: bool, task_name: str) -> list:
    #  When using shell, pass the command  'as is'
    if shell:
        return [command]
    try:
        return shlex.split(command)
    except ValueError as e:
        raise TaskException("Illegal command '{}' for task '{}' - {}".format(command, task_name, e))


def _active_task_name(config: Config, args) -> str:
    task_name = config.setting(Config.DEFAULT_TASK) if args.task is None else args.task
    if task_name is None:
        raise TaskException("No main task name was given")
    return task_name


def _parse_env_string(s: str):
    parts = s.split('=', maxsplit=1)
    if len(parts) == 1:
        return s, ""
    return parts[0], str(parts[1])


def _set_command_args(task: dict, args: Args) -> None:
    if args.shell is not None:
        task[TaskKeys.SHELL] = args.shell
    if args.stop_on_error is not None:
        task[TaskKeys.STOP_ON_ERROR] = args.stop_on_error

    if args.command:
        task[TaskKeys.COMMANDS] = args.command
    elif args.command_append:
        task[TaskKeys.COMMANDS] += args.append_command

    envs = []
    if args.env:
        envs = args.env
        task[TaskKeys.ENV] = {}
    elif args.env_append:
        envs = args.env_append

    for e in envs:
        e_name, e_value = _parse_env_string(e)
        task[TaskKeys.ENV][e_name] = e_value

def execute_task(config: Config, args: Args) -> int:
    task_name = _active_task_name(config, args)
    task: dict = config.task(task_name)
    _set_command_args(task, args)

    cmds = task[TaskKeys.COMMANDS]
    if len(cmds) == 0:
        print("No commands defined for task '{}'. Nothing to do.".format(task_name))
        return 0

    rc = 0
    for cmd_str in task[TaskKeys.COMMANDS]:
        cmd_str = expand_string(cmd_str, config.defs)
        cmd_array = _gen_command_array(cmd_str, task[TaskKeys.SHELL], task_name)
        try:
            env = task.get(TaskKeys.ENV, None)
            if env is not None:
                penv = os.environ.copy()
                penv.update(env)
            else:
                penv = None
            p = subprocess.Popen(cmd_array, shell=task[TaskKeys.SHELL], stdout=sys.stdout,
                                 stderr=sys.stderr, env=penv)
            cmd_rc = p.wait()
        except (OSError, FileNotFoundError) as e:
            raise TaskException("Error occured running command '{}' - {}".format(cmd_str, e))
        if cmd_rc == 0:
            continue
        if task[TaskKeys.STOP_ON_ERROR]:
            return cmd_rc
        if rc == 0:
            rc = cmd_rc
    return rc


def list_tasks(config: Config):
    PRINT_FMT = "{:<2}{:<24}{:<55}"
    print(PRINT_FMT.format("L", "Name", "Description"))
    print(PRINT_FMT.format("-", "-----", "-----------"))
    local_tasks = config.local_tasks.keys()
    for task_name in local_tasks:
        if task_name in config.supressed_tasks:
            continue
        task: dict = config.task(task_name)
        desc = task.get(TaskKeys.SHORT_DESC, "")
        if len(desc) > 55:
            desc = desc[:52] + "..."
        print(PRINT_FMT.format("l", task_name, desc[-55:], "l"))
    for task_name in config.global_tasks.keys():
        if task_name in local_tasks or task_name in config.supressed_tasks:
            continue
        task: dict = config.task(task_name)
        desc = task.get(TaskKeys.SHORT_DESC, "")
        print(PRINT_FMT.format("g", task_name, desc, "l"))


def dump_task(config: Config, args: Args):
    task_name = _active_task_name(config, args)
    task = config.task(task_name)
    if args.exapnd:
        for i in range(len(task[TaskKeys.COMMANDS])):
            task[TaskKeys.COMMANDS][i] = expand_string(task[TaskKeys.COMMANDS][i], config.defs)
    print(json.dumps(task, indent=4))


def show_task_info(config: Config, args: Args):
    PRINT_FMT = "{:<24}{:<80}"
    task_name = _active_task_name(config, args)
    task: dict = config.task(task_name)
    _set_command_args(task, args)
    task_keys = task.keys()

    def print_val(title, value):
        print(PRINT_FMT.format("{}".format(title), value))

    def print_task_val(title, key):
        if key in task_keys:
            print_val(title, task[key])

    def print_task_bool(title, key):
        if key in task_keys:
            print_val(title, "Yes" if task[key] else "No")

    def print_blob(title, text):
        first = True
        for line in text.split('\n'):
            for in_line in textwrap.wrap(line, width=80):
                if first:
                    print_val(title, in_line)
                    first = False
                    continue
                print(PRINT_FMT.format("", in_line))

    def print_task_blob(title, key):
        if key not in task_keys:
            return
        print_blob(title, task[key])

    print(PRINT_FMT.format("Task name:", task_name))
    print_task_val("Short description:", TaskKeys.SHORT_DESC)
    print_task_blob("Description:", TaskKeys.LONG_DESC)
    print_task_bool("Use shell:", TaskKeys.SHELL)
    print_task_bool("Stop on error:", TaskKeys.STOP_ON_ERROR)

    cmds: list = task[TaskKeys.COMMANDS]
    if len(cmds) == 0:
        print("NOTICE: No commands defined for task")
        return
    if len(cmds) == 1:
        print_blob("Command", cmds[0])
        return
    print(PRINT_FMT.format("Commands:", ""))
    count = 0
    for cmd_str in cmds:
        print_blob("     [{}]".format(count), expand_string(cmd_str, config.defs))
        count += 1
