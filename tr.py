from config import *
import argparse
import actions
import argcomplete
import sys


def _tasks_complete(**kwargs):
    try:
        parsed_args: argparse.Namespace = kwargs['parsed_args']
        parser_name = parsed_args.subparsers_name
    except (KeyError, AttributeError):
        return []
    if (parser_name == "run" or parser_name == "info" or parser_name == "dump") \
       and parsed_args.task is None:
        return Config(None, [], []).visible_tasks()
    return []


def _parse_arguments():
    try:
        ex_args_idx = sys.argv.index('--')
        tr_argv = sys.argv[1:ex_args_idx]
        cmds_argv = sys.argv[ex_args_idx + 1:]
    except ValueError:
        tr_argv = sys.argv[1:]
        cmds_argv = []
    yes_no: typing.List[str] = [TASK_YES_TOKEN, TASK_NO_TOKEN]
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='count', help='log file verbosity', default=0)
    parser.add_argument('-C', '--conf', metavar='CONF', help='configuration file to use',
                        default=None)
    parser.add_argument('--log_file', metavar='FILE', help='set log file', default='')
    parser.add_argument('-V', '--variable', metavar='VAR', default=None, action='append',
                        help='set a variable')
    subparsers = parser.add_subparsers(help='commands', dest='subparsers_name')
    subparsers.required = True

    task_target_parser = argparse.ArgumentParser(add_help=False)
    task_target_parser.add_argument('task', nargs='?', metavar='TASK', default=None,
                                    help='set task')
    run_parser = subparsers.add_parser('run', help='execute a task', parents=[task_target_parser])
    run_parser.add_argument('-c', '--command', metavar='CMD', default=None, action='append',
                            help='set command to run')
    run_parser.add_argument('--cwd', metavar='DIR', default=None, help='set working directory')
    run_parser.add_argument('--shell', type=str, choices=yes_no, action='store', default=None,
                            help='set shell usage')
    run_parser.add_argument('--shell-path', metavar='PATH', help='set shell path', default=None)
    run_parser.add_argument('--stop-on-error', choices=yes_no, action='store', default=None,
                            help='set stop behavior on command error')
    run_parser.add_argument('--env', metavar='ENV=VAL', default=None, action='append',
                            help='set an environment variable')
    run_parser.add_argument('-s', '--summary', action='store_true', default=False,
                            help='show task summary before run')

    #  Container specific arguments
    run_parser.add_argument('--c-image', metavar='IMAGE',
                            help='set image or container to run the task in')
    run_parser.add_argument('--c-tool', metavar='TOOL',
                            help='set container tool to use')
    run_parser.add_argument('--c-volume', metavar='VOLUME', action='append', default=None,
                            help='set container volume')
    run_parser.add_argument('--c-tty', choices=yes_no, action='store', default=None,
                            help='set container tty allocation')
    run_parser.add_argument('--c-interactive', choices=yes_no, action='store', default=None,
                            help='set container interactive mode')

    cont_run_type_grp = run_parser.add_mutually_exclusive_group()
    cont_run_type_grp.add_argument('--c-rm', type=str, choices=yes_no, action='store', default=None,
                                   help='set container removal after run')
    cont_run_type_grp.add_argument('--c-exec', action='store_true', default=False,
                                   help='run command in existing container')
    run_parser.add_argument('--c-flags', metavar='FLAGS', default=None,
                            help='set container flags')
    run_parser.add_argument('--c-shell', type=str, choices=yes_no, action='store', default=None,
                            help='wrap container command in shell')
    run_parser.add_argument('--c-shell-path', metavar='PATH', default=None,
                            help='set container shell path')
    run_parser.add_argument('--c-env', metavar='ENV=VAL', default=None, action='append',
                            help='set container environment variable')
    run_parser.add_argument('--c-cwd', metavar='DIR', default=None,
                            help='set container working directory')

    subparsers.add_parser('info', help='show task info', parents=[task_target_parser])
    dump_parser = subparsers.add_parser('dump', help='dump a task', parents=[task_target_parser])
    dump_parser.add_argument('--raw', help='show raw task', action='store_true', default=False)
    list_parser = subparsers.add_parser('list', help='list tasks')
    list_parser.add_argument('-a', '--all', action='store_true', default=False,
                             help='show hidden and shadowed tasks')
    list_parser.add_argument('--names-only', action='store_true', default=False,
                             help=argparse.SUPPRESS)

    subparsers.add_parser('schema_dump', help='dump configuration schema')
    subparsers.add_parser('config_dump', help='dump configuration')

    # TODO: Not sure what pyright wants with this type ignore
    argcomplete.autocomplete(parser, always_complete_options=False,
                             default_completer=_tasks_complete)  # type: ignore
    return parser.parse_args(tr_argv), cmds_argv


if __name__ == "__main__":
    args, cmds_args = _parse_arguments()
    init_logging(args.log_file, args.verbose)

    info("args='{}'", sys.argv[1:])
    info("cmd_args={}", cmds_args)
    try:

        if args.subparsers_name == "schema":
            Schema.dump()
            exit(0)

        config = Config(args.conf, args.variable, cmds_args)
        if args.subparsers_name == "list":
            actions.list_tasks(config, args.all, args.names_only)
        elif args.subparsers_name == "info":
            actions.show_task_info(args=args, config=config)
        elif args.subparsers_name == "schema_dump":
            actions.dump_task(config, args)
        elif args.subparsers_name == "config_dump":
            actions.dump_config(config)
        elif args.subparsers_name == "dump":
            actions.dump_task(config, args)
        else:
            exit(actions.run_task(config, args))

    except TaskException as e:
        error_and_print(str(e))
        exit(1)
