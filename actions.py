from common import *
from Task import *
import textwrap

def _active_task_name(config: Config, args) -> str:
    task_name = config.default_task_name() if args.task is None else args.task
    if task_name is None:
        raise TaskException("No main task name was given")
    return task_name


__PRINT_FMT = "{:<24}{:<80}"
def show_task_info(args: Args, config: Config, full_details: bool) -> None:
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
        ret = expand_string(cmd_str, None, config.defs).strip()
        if len(ret) == 0:
            return "n/a (empty command)"
        return ret

    task_name = _active_task_name(config, args)
    task = Task(config.task(task_name), task_name, config)
    print_val("Task name:", task.name)
    if full_details:
        print_val("Short description:", task.short_desc)
        if task.long_desc:
            print_blob("Description:", task.long_desc)
        print_bool("Abstract", task.abstract)
        print_bool("Global:", task.global_task)
    print_bool("Use shell: ", task.shell is not None)
    if task.shell:
        shell_title = "Shell path:"
        if task.shell:
            print_val(shell_title, task.shell)
        else:
            print_val(shell_title, "default (/usr/bin/sh)")
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
        print_bool("  Use shell: ", task.c_shell is not None)
        if task.c_shell:
            print_val( "  Shell path:", task.c_shell)
        if task.c_flags:
            print_blob("  Run/Exec flags:", task.c_flags)
        if len(task.c_volumes) == 1:
            print_blob("  Volume:", info_expanded_str(task.c_volumes[0]))
        elif len(task.c_volumes) > 1:
            count = 0
            print(__PRINT_FMT.format("  Volumes:", ""))
            for vol in task.c_volumes:
                print_blob("     [{}]".format(count), info_expanded_str(vol))
                count += 1

    if len(task.commands) == 0:
        print("NOTICE: No commands defined for task")
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

def list_tasks(config: Config):
    PRINT_FMT = "{:<24}{:<3}{:<55}"
    default_task_name = config.default_task_name()
    local_tasks = config.local_tasks.keys()

    def print_task(name: str, task: dict, local: bool):
        #  Don't show:
        #  1. Abstract tasks
        #  2. Global tasks overridden by local tasks
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
    if not config.setting(ConfigSchema.Keys.AllowGlobal, True):
        return
    for task_name in config.global_tasks.keys():
        print_task(task_name, config.task(task_name), local=False)


def run_task(config: Config, args: Args) -> int:
    task_name = _active_task_name(config, args)
    task = Task(config.task(task_name), task_name, config)
    task.args_update(args)
    return task.run()

def dump_task(config: Config, args: Args):
    task_name = _active_task_name(config, args)
    print(json.dumps(config.task(task_name, raw=True), indent=4))