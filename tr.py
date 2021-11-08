#!/bin/python3
from common import *
from config import *
import argparse
import actions


def _parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--define', metavar='DEFINE', default=None, action='append',
                        help='Set a deinifion')
    subparsers = parser.add_subparsers(help='commands', dest='subparsers_name')
    subparsers.required = True

    task_target_parser = argparse.ArgumentParser(add_help=False)
    task_target_parser.add_argument('task', nargs='?', metavar='TASK', default=None,
                                    help='Set task')
    run_parser = subparsers.add_parser('run', help='Execute a task', parents=[task_target_parser])
    run_parser.add_argument('-c', '--command', metavar='CMD', default=None, action='append',
                            help='Set command to run')
    run_parser.add_argument('--cwd', metavar='DIR', default=None, help='Set working direcotry')
    run_parser.add_argument('--shell', action=argparse.BooleanOptionalAction, default=None,
                            help='Set shell usage')
    run_parser.add_argument('--shell-path', metavar='PATH', help='Set shell path', default=None)
    run_parser.add_argument('--stop-on-error', action=argparse.BooleanOptionalAction,
                            help='Set stop on first error behavior')

    run_parser.add_argument('-e', '--env', metavar='ENV', default=None, action='append',
                            help='Set an environment variable')
    run_parser.add_argument('-a', '--args', metavar='ARGS', default=None,
                            help='Set command arguments')
    run_parser.add_argument('-s', '--summary', action='store_true', default=False,
                            help='show task summary before run')

    #  Container specific arguments
    run_parser.add_argument('--c-image', metavar='IMAGE',
                            help='Set image or container to run the task in')
    run_parser.add_argument('--c-tool', metavar='TOOL',
                            help='Set container tool to use')
    run_parser.add_argument('--c-volume', metavar='VOLUME', action='append', default=None,
                            help='Set container volume')
    run_parser.add_argument('--c-tty', action=argparse.BooleanOptionalAction, default=None,
                            help='Set container tty allocation')
    run_parser.add_argument('--c-interactive', action=argparse.BooleanOptionalAction,
                            default=None, help='Set container interactive mode')

    cont_run_type_grp = run_parser.add_mutually_exclusive_group()
    cont_run_type_grp.add_argument('--c-rm', action=argparse.BooleanOptionalAction, default=None,
                                   help='Set container removal after run')
    cont_run_type_grp.add_argument('--c-exec', action='store_true', default=False,
                                   help='Run command in existing container')
    run_parser.add_argument('--c-flags', metavar='FLAGS', default=None,
                            help='Set Container flags')
    run_parser.add_argument('--c-shell', action=argparse.BooleanOptionalAction, default=None,
                            help='Wrap container command in shell')
    run_parser.add_argument('--c-shell-path', metavar='PATH', default=None,
                            help='Set container shell path')
    run_parser.add_argument('--c-env', metavar='ENV', default=None, action='append',
                            help='Set container environment variable')
    run_parser.add_argument('--c-cwd', metavar='DIR', default=None,
                            help='Set container working direcotry')

    global_opt_parser = argparse.ArgumentParser(add_help=False)
    global_opt_parser.add_argument('-g', '--global_task', action='store_true', default=False,
                                   help='Global task only')
    subparsers.add_parser('info', help='Show task info',
                          parents=[task_target_parser, global_opt_parser])
    subparsers.add_parser('dump', help='Dump a task',
                          parents=[task_target_parser, global_opt_parser])
    list_parser = subparsers.add_parser('list', help='List tasks')
    list_parser.add_argument('-a', '--all', action='store_true', default=False,
                             help='Show hidden and shadowed tasks')

    return parser.parse_args()


if __name__ == "__main__":
    init_logging()
    try:
        args = _parse_arguments()
        config = Config(args.define)
        if args.subparsers_name == "list":
            actions.list_tasks(config, args.all)
        elif args.subparsers_name == "info":
            actions.show_task_info(args=args, config=config)
        elif args.subparsers_name == "dump":
            actions.dump_task(config, args)
        else:
            exit(actions.run_task(config, args))

    except TaskException as e:
        print(str(e))
        exit(1)
