from tr.Task import *
import textwrap
from argparse import Namespace as Args


def _active_task_name(config: Config) -> str:
    if config.args and config.args.task:
        task = config.args.task
    else:
        task = config.default_task_name()
    if task is None:
        raise TaskException("No main task name was given")
    return task


def _show_task(task: Task, full_details: bool) -> None:
    def print_val(title: str, value: typing.Any) -> None:
        print(f"{title:<24}{value:<}")

    def print_bool(title, value: bool) -> None:
        print_val(title, "Yes" if value else "No")

    def print_blob(title: str, text: str) -> None:
        if text is None or len(text) == 0:
            print(title)
            return
        first = True
        for line in text.split('\n'):
            for in_line in textwrap.wrap(line, width=80):

                if first:
                    print_val(title, in_line)
                    first = False
                    continue
                print_val("", in_line)

    def _task_str(cmd_str: str) -> str:
        if len(cmd_str.strip()) == 0:
            return "[n/a - empty string)]"
        return cmd_str

    print_val("Task name:", task.name)
    if full_details:
        if task.short_desc:
            print_val("Short description:", task.short_desc)
        if task.long_desc:
            print_blob("Description:", task.long_desc)
        print_bool("Hidden:", task.hidden)
        print_bool("Abstract:", task.abstract)
    print_bool("Use shell: ", task.shell)
    if task.shell:
        shell_title = "Shell path:"
        if task.shell_path is None:
            print_val(shell_title, "/usr/bin/sh")
        else:
            print_val(shell_title, task.shell_path)
    print_bool("Inherit environment", task.env_inherit)
    count = 0
    if task.env:
        print("Environment:")
        for k, v in task.env.items():
            print_blob(f"     [{count}]", f"{k}={v}")
            count += 1
    if task.cwd:
        print_blob("Working directory:", _task_str(task.cwd))

    if task.c_image:
        print("Container details:")
        image = _task_str(task.c_image)
        if task.c_exec:
            print_val("  Execute in:", image)
        else:
            print_val("  Run image:", image)
            print_bool("  Remove:", task.c_rm)
        print_bool("  Interactive:", task.c_interactive)
        print_bool("  Allocate tty:", task.c_tty)
        print_bool("  Use shell: ", task.c_shell)
        if task.c_shell:
            print_val("  Shell path:", task.c_shell_path)
        if task.c_flags:
            print_blob("  Run/Exec flags:", task.c_flags)
        if task.c_cwd:
            print_blob("  Working directory:", _task_str(task.c_cwd))
        if len(task.c_volumes) == 1:
            print_blob("  Volume:", _task_str(task.c_volumes[0]))
        elif len(task.c_volumes) > 1:
            count = 0
            print("  Volumes:")
            for vol in task.c_volumes:
                print_blob(f"       [{count}]", _task_str(vol))
                count += 1
        if task.c_env:
            print("  Environment:")
            for k, v in task.c_env.items():
                print_blob(f"       [{count}]", f"{k}={v}")
                count += 1

    if len(task.commands) == 0:
        if task.c_image is None:
            print("NOTICE: No commands defined for task")
        else:
            print("NOTICE: Will run the image/container default command")
        return
    if len(task.commands) == 1:
        print_blob("Command:", _task_str(task.commands[0]))
        return

    print_bool("Stop on error:", task.stop_on_error)
    print("Commands:")
    count = 0
    for cmd in task.commands:
        print_blob(f"     [{count}]", _task_str(cmd))
        count += 1


def show_task_info(config: Config) -> None:
    task_name = _active_task_name(config)
    task = Task(task_name, config)
    if config.args.expand:
        task.expand()
    _show_task(task, True)


def list_tasks(config: Config) -> None:
    def _display_token(token: Optional[str], max_len: int) -> str:
        if not token:
            return ""
        if len(token) < max_len:
            return token
        return f"{token[:max_len - 3]}..."

    _max_name_print_len = 40
    _max_desc_print_len = 55
    _flags_str_len = 10
    # 2 for spaces between description and flags
    _error_max_str_len = _max_desc_print_len + _flags_str_len + 2
    show_all: bool = config.args.all
    names_only: bool = config.args.names_only
    info("Listing tasks show_all={} names_only={}", show_all, names_only)
    #  This is hard to decipher, but '{{}}' is a way to escape a '{}'
    print_fmt = f"{{:<{_max_name_print_len}}}  {{:<{_flags_str_len}}}  {{}}"
    err_print_fmt = f"{{:<{_max_name_print_len}}}  {{}}"
    default_task_name = config.default_task_name()

    if not names_only:
        print(print_fmt.format("Name", "Flags", "Description"))
        print(print_fmt.format("----", "-----", "-----------"))
    for task_name in sorted([*config.tasks]):
        try:
            t = Task(task_name, config=config)
        except TaskException as e:
            error_str = _display_token(f"<error: {e}>", _error_max_str_len)
            name_str = _display_token(task_name, _max_name_print_len)
            print(err_print_fmt.format(name_str, error_str))
            continue
        if not show_all and (t.hidden or t.abstract):
            continue
        if names_only:
            print(task_name, end=' ')
            continue

        flags = ""
        if t.abstract:
            flags += "A"
        elif t.hidden:
            flags += "H"
        elif task_name == default_task_name:
            flags += "*"

        print(print_fmt.format(_display_token(task_name, _max_name_print_len),
              flags, _display_token(t.short_desc, _max_desc_print_len)))


def args_update(task, args: Args) -> None:
    if args.stop_on_error:
        task.stop_on_error = args.stop_on_error
    if args.command:
        task.commands = args.command
    if args.cwd:
        task.cwd = args.cwd
    if args.shell:
        task.shell = (args.shell == TASK_YES_TOKEN)
    if args.shell_path:
        task.shell_path = args.shell_path
    if args.env:
        task.env = {}
        for e in args.env:
            e_name, e_value = parse_assignment_str(e)
            task.env[e_name] = e_value

    if args.c_image:
        task.c_image = args.c_image
    if args.c_volume:
        task.c_volumes = args.c_volume
    if args.c_interactive:
        task.c_interactive = (args.c_interactive == TASK_YES_TOKEN)
    if args.c_tty:
        task.c_tty = (args.c_tty == TASK_YES_TOKEN)
    if args.c_flags:
        task.c_flags = args.c_flags
    if args.c_exec:
        task.c_exec = args.c_exec
    if args.c_rm:
        task.c_rm = (args.c_rm == TASK_YES_TOKEN)
    if args.c_tool:
        task.c_tool = args.c_tool
    if args.c_shell:
        task.c_shell = (args.c_shell == TASK_YES_TOKEN)
    if args.c_shell_path:
        task.c_shell_path = args.c_shell_path
    if args.c_cwd:
        task.c_cwd = args.c_cwd
    if args.c_env:
        task.c_env = {}
        for e in args.c_env:
            e_name, e_value = parse_assignment_str(e)
            task.c_env[e_name] = e_value
    for v in args.variable:
        key, val = parse_assignment_str(v)
        task.vars_map[key] = val


def run_task(config: Config) -> int:
    task_name = _active_task_name(config)
    info("Running task '{}'", task_name)
    task = Task(task_name, config)
    args_update(task, config.args)
    task.expand()
    if config.args.summary:
        _show_task(task, False)
        print("-" * 70)
        sys.stdout.flush()
    return task.run()


def dump_task(config: Config) -> None:
    task_name = _active_task_name(config)
    print(json.dumps(config.get_task_desc(task_name, config.args.includes), indent=4))


def dump_config(config: Config) -> None:
    print(json.dumps(config.conf, indent=4))
