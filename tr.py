#!/bin/python3
from common import *
from config import *
import argparse
from argparse import Namespace as Args
from Task import Task


def _parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("task", nargs='?', metavar='TASK', default=None, help='Set task to run')
    show_group = parser.add_mutually_exclusive_group(required=False)
    show_group.add_argument("-l", "--list", action='store_true', help='List tasks')
    show_group.add_argument("-i", "--info", action='store_true', help='Show task info')
    show_group.add_argument("-d", "--dump", action='store_true', help=argparse.SUPPRESS)
    parser.add_argument("-x", "--exapnd",  action='store_true', default=False,
                        help=argparse.SUPPRESS)
    parser.add_argument("-c", "--command", metavar='CMD', default=None, action='append',
                        help='Set command to run')
    parser.add_argument("--cwd", metavar='DIR', default=None, help='Set working direcotry')
    parser.add_argument("--shell", action=argparse.BooleanOptionalAction, default=None,
                        help='Set shell usage')
    parser.add_argument("--shell-path", metavar='PATH', help='Set shell path', default=None)
    parser.add_argument("--stop-on-error", action=argparse.BooleanOptionalAction,
                        help='Set stop on first error behavior')

    parser.add_argument("-e", "--env", metavar='ENV', default=None, action='append',
                        help='Set environment variable')
    parser.add_argument("-a", "--args", metavar='ARGS', action='append', default=[],
                        help='Set args for commands')

    #  Container specific arguments
    parser.add_argument("--c-image", metavar='IMAGE',
                        help='Set image or container to run the task in')
    parser.add_argument("--c-tool", metavar='TOOL',
                        help='Set container tool to use')
    parser.add_argument("--c-volume", metavar='VOLUME', action='append', default=None,
                        help='Set container volume')
    parser.add_argument("--c-tty", action=argparse.BooleanOptionalAction, default=None,
                        help='Set container tty allocation')
    parser.add_argument("--c-interactive", action=argparse.BooleanOptionalAction, default=None,
                        help='Set container interactive mode')

    cont_run_type_grp = parser.add_mutually_exclusive_group()
    cont_run_type_grp.add_argument("--c-rm", action=argparse.BooleanOptionalAction, default=None,
                                   help='Set container removal after run')
    cont_run_type_grp.add_argument("--c-exec", action="store_true", default=False,
                                   help='Run command in existing container')
    parser.add_argument("--c-flags", metavar='FLAGS', default=None, help='Set Container flags')

    return parser.parse_args()


def _active_task_name(config: Config, args) -> str:
    task_name = config.default_task_name() if args.task is None else args.task
    if task_name is None:
        raise TaskException("No main task name was given")
    return task_name


def execute_task(config: Config, args: Args) -> int:
    task_name = _active_task_name(config, args)
    task = Task(config.task(task_name), task_name, config, args)
    return task.execute()


def list_tasks(config: Config):
    PRINT_FMT = "{:<24}{:<3}{:<55}"
    default_task_name = config.default_task_name()
    local_tasks = config.local_tasks.keys()

    def print_task(name: str, task: dict, local: bool):
        # Don't show supressed tasks and global tasks overridden by local tasks
        if task.get(TaskSchema.Keys.Abstract, False) or (not local and name in local_tasks):
            return
        default = name == default_task_name
        desc = task.get(TaskSchema.Keys.ShortDesc, "")
        if len(desc) > 55:
            desc = desc[:52] + "..."
        flags = "{}{}".format("*" if default else " ", "l" if local else "g")
        print(PRINT_FMT.format(task_name, flags, desc[-55:]))

    print(PRINT_FMT.format("Name", "DL", "Description"))
    print(PRINT_FMT.format("----", "--", "-----------"))
    for task_name in local_tasks:
        print_task(task_name, config.task(task_name), local=True)
    for task_name in config.global_tasks.keys():
        print_task(task_name, config.task(task_name), local=False)


def show_task_info(config: Config, args: Args):
    task_name = _active_task_name(config, args)
    task = Task(config.task(task_name), task_name, config, args)
    task.show_info()


def dump_task(config: Config, args: Args):
    task_name = _active_task_name(config, args)
    print(json.dumps(config.task(task_name, raw=True), indent=4))


if __name__ == "__main__":
    init_logging()
    try:
        config = Config()
        args = _parse_arguments()
        if args.list:
            list_tasks(config)
        elif args.info:
            show_task_info(config, args)
        elif args.dump:
            dump_task(config, args)
        else:
            exit(execute_task(config, args))

    except TaskException as e:
        print(str(e))
        exit(1)
