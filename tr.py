#!/bin/python3
from common import *
from config import *
from actions import *
import argparse


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
    parser.add_argument("--shell", action=argparse.BooleanOptionalAction, default=None,
                        help='Set shell usage')
    parser.add_argument("--stop-on-error", action=argparse.BooleanOptionalAction,
                        help='Set stop on first error behavior')
    #  parser.add_argument("-D", "--def", help='Set a definition', metavar='DEF')
    env_group = parser.add_mutually_exclusive_group(required=False)
    env_group.add_argument("-e", "--env", metavar='CMD', default=None, action='append',
                          help='Set environment variable (replace config values)')
    env_group.add_argument("-E", "--env-append", metavar='CMD', default=None, action='append',
                           help='Set environment variable (append to config values)')
    parser.add_argument("-a", "--args", metavar='ARGS', help='Set args for commands')

    parser.add_argument("task", nargs='?', metavar='TASK', default=None, help='Set task to run')

    return parser.parse_args()


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
