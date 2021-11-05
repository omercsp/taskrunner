from common import *
from Task import *
import subprocess

def _container_execute(task: Task, command: str) -> int:
    cmd_array = [task.c_tool]
    cmd_array.append("exec" if task.c_exec else "run")
    if task.cwd:
        cmd_array += ["-w", task.cwd]
    if task.c_interactive:
        cmd_array.append("-i")
    if task.c_tty:
        cmd_array.append("-t")
    if task.c_rm:
        cmd_array.append("--rm")

    for v in task.c_volumes:
        cmd_array += ["-v", v]

    if task.args.c_flags:
        cmd_array += task.args.c_flags.split()

    cmd_array.append(task.c_image)
    if task.shell:
        shell = "/usr/bin/sh" if task.shell_path is None else task.shell_path
        command = "\"{}\"".format(command)
        cmd_array += [shell, "-c", "\"{}\"".format(command)]
    else:
        cmd_array += [command]
    print(" ".join(cmd_array))
    p = subprocess.Popen(cmd_array, stdout=sys.stdout, stderr=sys.stderr)
    return p.wait()


def _parse_assignmet_str(s: str):
    parts = s.split('=', maxsplit=1)
    if len(parts) == 1:
        return s, ""
    return parts[0], str(parts[1])

def _system_execute(task: Task, cmd_str: str) -> int:
    if task.shell:
        cmd_array = [cmd_str]
    else:
        try:
            cmd_array = shlex.split(cmd_str)
        except ValueError as e:
            raise TaskException("Illegal command '{}' for task '{}' - {}".format(
                cmd_str, task.name, e))
    try:
        if task.env is None:
            penv = None
        else:
            penv = os.environ.copy()
            penv.update(task.env)
        p = subprocess.Popen(cmd_array, shell=task.shell, executable=task.shell_path,
                             stdout=sys.stdout, stderr=sys.stderr, env=penv, cwd=task.cwd)
        return p.wait()

    except (OSError, FileNotFoundError) as e:
        raise TaskException("Error occured running command '{}' - {}".format(cmd_str, e))

def execute(task: Task) -> int:
    if task.abstract:
        raise TaskException("Task '{}' is abstract, and can't be ran directly")
    if task.global_task and not task.config.setting(ConfigSchema.Keys.AllowGlobal, True):
        raise TaskException("Global tasks aren't allowed from this location")

    if not task.c_image and len(task.commands) == 0:
        print("No commands defined for task '{}'. Nothing to do.".format(task.name))
        return 0

    rc = 0
    for cmd in task.commands:
        if task.c_image:
            cmd_rc = _container_execute(task, cmd)
        else:
            cmd_rc = _system_execute(task, cmd)
        if cmd_rc == 0:
            continue
        if task.stop_on_error:
            return cmd_rc
        if rc == 0:
            rc = cmd_rc
    return rc
