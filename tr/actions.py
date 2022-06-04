from tr.Task import *
import textwrap


def _active_task_name(config: Config, args) -> str:
    task_name = config.default_task_name() if args.task is None else args.task
    if task_name is None:
        raise TaskException("No main task name was given")
    return task_name


def _show_task(task: Task, full_details: bool) -> None:
    def print_val(title: str, value: typing.Any):
        print(f"{title:<24}{value:<}")

    def print_bool(title, value: bool):
        print_val(title, "Yes" if value else "No")

    def print_blob(title: str, text: str):
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
        print_bool("Hidden", task.hidden)
        print_bool("Abstract", task.abstract)
    print_bool("Use shell: ", task.shell)
    if task.shell:
        shell_title = "Shell path:"
        if task.shell_path is None:
            print_val(shell_title, "/usr/bin/sh")
        else:
            print_val(shell_title, task.shell_path)
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


def show_task_info(args: Args, config: Config) -> None:
    task_name = _active_task_name(config, args)
    task = Task(task_name, config)
    if args.expand:
        task.expand_args(config.expander)
    _show_task(task, True)


def list_tasks(config: Config, show_all: bool, names_only: bool):
    info("Listing tasks show_all={} names_only={}", show_all, names_only)
    print_fmt = "{:<24}{:<6}{}"
    err_print_fmt = "{:<30}{}"
    default_task_name = config.default_task_name()

    if not names_only:
        print(print_fmt.format("Name", "Flags", "Description"))
        print(print_fmt.format("----", "-----", "-----------"))
    for task_name in sorted([*config.tasks]):
        try:
            t = Task(task_name, config=config)
        except TaskException as e:
            print(err_print_fmt.format(task_name, f"<error: {e}>"))
            continue
        if not show_all and (t.hidden or t.abstract):
            continue
        if names_only:
            print(task_name, end=' ')
            continue

        if t.short_desc:
            desc = t.short_desc if len(t.short_desc) <= 55 else t.short_desc[:52] + "..."
        else:
            desc = ""

        flags = ""
        if t.abstract:
            flags += "A"
        elif t.hidden:
            flags += "H"
        elif task_name == default_task_name:
            flags += "*"

        print(print_fmt.format(task_name, flags, desc[-55:]))


def run_task(config: Config, args: Args) -> int:
    task_name = _active_task_name(config, args)
    info("Running task '{}'", task_name)
    task = Task(task_name, config)
    task.args_update(args)
    task.expand_args(config.expander)
    if args.summary:
        _show_task(task, False)
        print("-" * 70)
        sys.stdout.flush()
    return task.run()


def dump_task(config: Config, args: Args):
    task_name = _active_task_name(config, args)
    print(json.dumps(config.get_task_desc(task_name, args.includes), indent=4))


def dump_config(config: Config):
    print(json.dumps(config.conf, indent=4))
