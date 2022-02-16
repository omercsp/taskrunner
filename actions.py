from Task import *
import textwrap


def _active_task_name(config: Config, args) -> str:
    task_name = config.default_task_name() if args.task is None else args.task
    if task_name is None:
        raise TaskException("No main task name was given")
    return task_name


__PRINT_FMT = "{:<24}{:<80}"


def _show_task(task: Task, config: Config, full_details: bool) -> None:
    def print_val(title: str, value: typing.Any):
        print(__PRINT_FMT.format("{}".format(title), value))

    def print_bool(title, value: bool):
        print_val(title, "Yes" if value else "No")

    def print_blob(title: str, text: str):
        if text is None or len(text) == 0:
            print(__PRINT_FMT.format(title, ""))
            return
        first = True
        for line in text.split('\n'):
            for in_line in textwrap.wrap(line, width=80):
                if first:
                    print_val(title, in_line)
                    first = False
                    continue
                print(__PRINT_FMT.format("", in_line))

    def info_expanded_str(cmd_str: str) -> str:
        ret = expand_string(cmd_str, config.defs).strip()
        if len(ret) == 0:
            return "[n/a - empty string)]"
        return ret

    print_val("Task name:", task.name)
    if full_details:
        print_val("Short description:", task.short_desc if task.short_desc else "")
        if task.long_desc:
            print_blob("Description:", task.long_desc)
        print_bool("Hidden", task.hidden)
        print_bool("Global:", task.global_task)
    print_bool("Use shell: ", task.shell)
    if task.shell:
        shell_title = "Shell path:"
        if task.shell_path is None:
            print_val(shell_title, "/usr/bin/sh")
        else:
            print_val(shell_title, task.shell_path)
    count = 0
    if task.env:
        print(__PRINT_FMT.format("Environment:", ""))
        for k, v in task.env.items():
            print_blob("     [{}]".format(count), "{}={}".format(k, v))
            count += 1
    if task.cwd:
        print_blob("Working directory:", info_expanded_str(task.cwd))

    if task.c_image:
        print_val("Container details:", "")
        if task.c_exec:
            print_val("  Execute in:", task.c_image)
        else:
            print_val("  Run image:", task.c_image)
            print_bool("  Remove:", task.c_rm)
        print_bool("  Interactive:", task.c_interactive)
        print_bool("  Allocate tty:", task.c_tty)
        print_bool("  Use shell: ", task.c_shell)
        if task.c_shell:
            print_val("  Shell path:", task.c_shell_path)
        if task.c_flags:
            print_blob("  Run/Exec flags:", task.c_flags)
        if task.c_cwd:
            print_blob("  Working directory:", info_expanded_str(task.c_cwd))
        if len(task.c_volumes) == 1:
            print_blob("  Volume:", info_expanded_str(task.c_volumes[0]))
        elif len(task.c_volumes) > 1:
            count = 0
            print(__PRINT_FMT.format("  Volumes:", ""))
            for vol in task.c_volumes:
                print_blob("     [{}]".format(count), info_expanded_str(vol))
                count += 1

    if len(task.commands) == 0:
        if task.c_image is None:
            print("NOTICE: No commands defined for task")
        else:
            print("NOTICE: Will run the image/container default command")
        return
    if len(task.commands) == 1:
        print_blob("Command:", info_expanded_str(task.commands[0]))
        return

    print_bool("Stop on error:", task.stop_on_error)
    print_val("Commands:", "")
    count = 0
    for cmd in task.commands:
        print_blob("     [{}]".format(count), info_expanded_str(cmd))
        count += 1


def show_task_info(args: Args, config: Config) -> None:
    task_name = _active_task_name(config, args)
    task = Task(task_name, args.global_task, config)
    _show_task(task, config, True)


def list_tasks(config: Config, show_all: bool, names_only: bool):
    info("Listing tasks show_all={} names_only={}".format(show_all, names_only))
    print_fmt = "{:<24}{:<6}{:<55}"
    err_print_fmt = "{:<24}{:<59}"
    default_task_name = config.default_task_name()
    local_tasks = config.local_tasks.keys()

    def print_task(task_name: str, glbl: bool) -> None:
        try:
            t = Task(task_name, glbl, config=config)
        except TaskException as e:
            print(err_print_fmt.format(task_name, "<error: {}>".format(str(e))))
            return
        if not show_all and t.hidden:
            return
        if names_only:
            print(task_name, end=' ')
            return

        if t.short_desc:
            desc = t.short_desc if len(t.short_desc) <= 55 else t.short_desc[:52] + "..."
        else:
            desc  = ""

        flags = "G" if t.global_task else "L"
        if t.hidden:
            flags += "H"
        if t.global_task and task_name in local_tasks:
            flags += "S"
        elif task_name == default_task_name:
            flags += "*"

        print(print_fmt.format(task_name, flags, desc[-55:]))

    if not names_only:
        print(print_fmt.format("Name", "Flags", "Description"))
        print(print_fmt.format("----", "-----", "-----------"))
    for task_name in local_tasks:
        print_task(task_name, False)
    if not config.setting(Schema.Keys.AllowGlobal, True):
        return
    for task_name in config.global_tasks.keys():
        if not show_all and task_name in local_tasks:
            continue
        print_task(task_name, True)


def run_task(config: Config, args: Args) -> int:
    task_name = _active_task_name(config, args)
    info("Running task '{}'", task_name)
    task = Task(task_name, False, config)
    task.args_update(args)
    if args.summary:
        _show_task(task, config, False)
        print("-" * 70)
        sys.stdout.flush()
    return task.run()


def dump_task(config: Config, args: Args):
    task_name = _active_task_name(config, args)
    if args.raw:
        print(json.dumps(config.raw_task(task_name), indent=4))
    else:
        print(json.dumps(config.task_descriptor(task_name), indent=4))
