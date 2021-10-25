#!/bin/python3
from common import *
from config import *
import argparse
from argparse import Namespace as Args
from Task import Task


def _parse_arguments():
    parser = argparse.ArgumentParser()
    show_group = parser.add_mutually_exclusive_group(required=False)
    show_group.add_argument("-l", "--list", action='store_true', help='List all tasks')
    show_group.add_argument("-i", "--info", action='store_true', help='Show task info')
    show_group.add_argument("-d", "--dump", action='store_true', help=argparse.SUPPRESS)
    parser.add_argument("-x", "--exapnd",  action='store_true', default=False,
                        help=argparse.SUPPRESS)
    commands_group = parser.add_mutually_exclusive_group(required=False)
    commands_group.add_argument("-c", "--command", metavar='CMD', default=None, action='append',
                                help='Set command to run (replace config values)')
    commands_group.add_argument("-C", "--command-append", metavar='CMD', default=None,
                                action='append',
                                help='Set command to run (append to config values)')

    parser.add_argument("--cwd", metavar='DIR', default=None, help='Set working direcotry')
    parser.add_argument("--shell", action=argparse.BooleanOptionalAction, default=None,
                        help='Set shell usage')
    parser.add_argument("--shell-path", metavar='PATH', help='Set shell path', default=None)
    parser.add_argument("--stop-on-error", action=argparse.BooleanOptionalAction,
                        help='Set stop on first error behavior')

    env_group = parser.add_mutually_exclusive_group(required=False)
    env_group.add_argument("-e", "--env", metavar='CMD', default=None, action='append',
                          help='Set environment variable (replace config values)')
    env_group.add_argument("-E", "--env-append", metavar='CMD', default=None, action='append',
                           help='Set environment variable (append to config values)')

    parser.add_argument("-I", "--image", metavar='IMAGE', help='Container image to run the task in')
    parser.add_argument("--container_tool", metavar='TOOL', help='Container image to run the task in')
    parser.add_argument("-a", "--args", metavar='ARGS', help='Set args for commands')

    parser.add_argument("task", nargs='?', metavar='TASK', default=None, help='Set task to run')

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

def show_task_info(config: Config, args: Args):
    task_name = _active_task_name(config, args)
    task = Task(config.task(task_name), task_name, config, args)
    task.show_info()

def dump_task(config: Config, args: Args):
    task_name = _active_task_name(config, args)
    task = config.task(task_name)
    if args.exapnd:
        for i in range(len(task[TaskKeys.COMMANDS])):
            task[TaskKeys.COMMANDS][i] = expand_string(task[TaskKeys.COMMANDS][i], config.defs)
    print(json.dumps(task, indent=4))


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
