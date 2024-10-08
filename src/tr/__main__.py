from tr.config import Config
from tr.common import TASK_YES_TOKEN, TASK_NO_TOKEN, TaskException, DictDumpFmt
from tr.config import Config, AutoVarsKeys
from tr.logTools import init_logging, info, error_and_print
from tr.actions import (run_task, list_tasks, show_task_info, dump_task, dump_config, dump_schema,
                        SchemaDumpOpts)
from tr import version
import argparse
import argcomplete
import sys

_RUN_CMD = "run"
_LIST_CMD = "list"
_INFO_CMD = "info"
_DUMP_TASK_CMD = "dump"
_DUMP_CONFIG_CMD = "dump_config"
_DUMP_SCHEMA_CMD = "dump_schema"


def _tasks_complete(**kwargs) -> list[str]:
    try:
        parsed_args: argparse.Namespace = kwargs['parsed_args']
        parser_name = parsed_args.subparsers_name
    except (KeyError, AttributeError):
        return []
    if (parser_name == _RUN_CMD or parser_name == _INFO_CMD or parser_name == _DUMP_TASK_CMD) \
       and parsed_args.task is None:
        return Config(None).visible_tasks()
    return []


def _parse_arguments() -> argparse.Namespace:
    try:
        ex_args_idx = sys.argv.index('--')
        tr_argv = sys.argv[1:ex_args_idx]
        cmds_argv = sys.argv[ex_args_idx + 1:]
    except ValueError:
        tr_argv = sys.argv[1:]
        cmds_argv = []
    yes_no: list[str] = [TASK_YES_TOKEN, TASK_NO_TOKEN]
    parser = argparse.ArgumentParser(prog='task')
    parser.add_argument('--version', action='version', version=f'%(prog)s {version}')
    parser.add_argument('-v', '--verbose', action='count', help='log file verbosity', default=0)
    parser.add_argument('-C', '--conf', metavar='CONF', help='configuration file to use',
                        default=None)
    parser.add_argument('--log_file', metavar='FILE', help='set log file', default='')
    subparsers = parser.add_subparsers(help='commands', dest='subparsers_name')
    subparsers.required = True

    task_target_parser = argparse.ArgumentParser(add_help=False)
    task_target_parser.add_argument('task', nargs='?', metavar='TASK', default=None,
                                    help='set task')
    task_target_parser.add_argument('-V', '--variable', metavar='VAR', default=[], action='append',
                                    help='set a variable')
    run_parser = subparsers.add_parser(_RUN_CMD, help='execute a task',
                                       parents=[task_target_parser])
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

    info_parser = subparsers.add_parser(_INFO_CMD, help='show task info',
                                        parents=[task_target_parser])
    info_parser.add_argument('-x', '--expand', help='expand values', action='store_true',
                             default=False)

    list_parser = subparsers.add_parser(_LIST_CMD, help='list tasks')
    list_parser.add_argument('-a', '--all', action='store_true', default=False,
                             help='show hidden and shadowed tasks')
    list_parser.add_argument('--names-only', action='store_true', default=False,
                             help=argparse.SUPPRESS)

    dump_common_parser = argparse.ArgumentParser(add_help=False)
    dump_common_parser.add_argument('-s', '--sort', action='store_true',
                                    default=False, help='sort by keys')
    dump_common_parser.add_argument('-f', '--format', choices=[e.value for e in DictDumpFmt],
                                    default=DictDumpFmt.YAML)
    dump_parser = subparsers.add_parser(_DUMP_TASK_CMD, help='dump a task',
                                        parents=[task_target_parser, dump_common_parser])
    dump_parser.add_argument('-i', '--includes', help='with inclusions',
                             action='store_true', default=False)

    dump_schme_parser = subparsers.add_parser(_DUMP_SCHEMA_CMD,
                                              help='dump configuration file schema',
                                              parents=[dump_common_parser])
    dump_schme_parser.add_argument('-t', '--type', choices=[e.value for e in SchemaDumpOpts],
                                   default=SchemaDumpOpts.ALL)

    subparsers.add_parser(_DUMP_CONFIG_CMD, help='dump configuration', parents=[dump_common_parser])

    # TODO: Not sure what pyright wants with this type ignore
    argcomplete.autocomplete(parser, always_complete_options=False,
                             default_completer=_tasks_complete)  # type: ignore
    try:
        args = parser.parse_args(tr_argv)
    except SystemExit:
        raise TaskException("")
    args.__setattr__(AutoVarsKeys.TASK_CLI_ARGS, cmds_argv)
    return args


def main() -> int:
    try:
        args = _parse_arguments()
        init_logging(args.log_file, args.verbose)

        info("args='{}'", sys.argv[1:])
        info("cmd_args={}", args.__getattribute__(AutoVarsKeys.TASK_CLI_ARGS))

        if args.subparsers_name == _DUMP_SCHEMA_CMD:
            dump_schema(args.type, args.sort, args.format)
            return 0

        config = Config(args)
        if args.subparsers_name == _RUN_CMD:
            return run_task(config)
        elif args.subparsers_name == _LIST_CMD:
            list_tasks(config)
        elif args.subparsers_name == _INFO_CMD:
            show_task_info(config)
        elif args.subparsers_name == _DUMP_CONFIG_CMD:
            dump_config(config, args.sort, args.format)
        elif args.subparsers_name == _DUMP_TASK_CMD:
            dump_task(config, args.sort, args.format)

    except TaskException as e:
        error_and_print(str(e))
        return 255
    return 0


if __name__ == "__main__":
    exit(main())
