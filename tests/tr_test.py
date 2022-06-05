import argparse
import argcomplete
import os
import json
import subprocess
import typing
import shlex


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TASKS_JSON_FILE = "tasks.json"
LOG_FILE = "/tmp/task_runner.log"
OUTPUT_DIR = f"{SCRIPT_DIR}/output"
INTERMEIDATE_EXPECTED = f"{SCRIPT_DIR}/intermediate.expected"


class TaskTestException(Exception):
    def __init__(self, error):
        self.error = error

    def __str__(self):
        return self.error


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-D', '--no-diff', action='store_true', default=False,
                        help='don\'t run diff against expected output')
    parser.add_argument('-C', '--no-colors', action='store_true', default=False,
                        help='don\'t show colored output')
    parser.add_argument('-s', '--stop_on_failure', action='store_true', default=False,
                        help='stop on test failure')
    parser.add_argument('--no-containers', action='store_true', default=False,
                        help='don\'t container based tests')
    parser.add_argument('--pkg', action='store_true', default=False,
                        help='assume taskrunner was installed by a package (pip)')
    ctool_grp = parser.add_mutually_exclusive_group()
    ctool_grp.add_argument('--ctool', choices=['docker', 'podman'], default='podman',
                        help='choose container tool')
    ctool_grp.add_argument('--ctool-path', default=None, help='set container tool path')
    parser.add_argument('task', nargs='*', metavar='TASKS', help='set task')
    argcomplete.autocomplete(parser, always_complete_options=False)
    return parser.parse_args()


class TestRunInfo(object):
    def __init__(self,  args: argparse.Namespace) -> None:
        file_path = f"{SCRIPT_DIR}/{TASKS_JSON_FILE}"
        try:
            self.tasks = json.load(open(file_path, 'r'))["tasks"]
        except (IOError, TypeError, ValueError, KeyError) as e:
            raise TaskTestException(f"Error parsing {file_path} - {e}")
        if args.task:
            self.task_list = args.task
        else:
            self.task_list = sorted(self.tasks.keys())
        self.diff = not args.no_diff
        self.stop_on_failure = args.stop_on_failure,
        self.taskname = args.task
        self.show_colors = not args.no_colors
        self.skip_container_tests = args.no_containers
        self.task_bin = "task" if args.pkg else f"{SCRIPT_DIR}/../task"
        self.ctool = args.ctool_path if args.ctool_path else args.ctool


def run_test_tasks(info: TestRunInfo) -> int:
    class Colors(object):
        BOLD = '\033[1m'
        GREEN = '\033[32m'
        ERROR = '\033[31m'
        RESET = '\033[m'
    if info.show_colors:
        OK_STR = Colors.GREEN + "OK" + Colors.RESET
        FAILED_STR = Colors.ERROR + "Failed" + Colors.RESET
    else:
        OK_STR = "OK"
        FAILED_STR = "Failed"

    base_cmd = "{} -V task_cmd={} --log_file={} run --c-tool={}".format(
        info.task_bin, info.task_bin, LOG_FILE, info.ctool)
    rc = 0
    for t_name in info.task_list:
        try:
            task = info.tasks[t_name]
        except KeyError:
            raise TaskTestException(f"Unknown task '{t_name}'")
        t_meta = task.get("meta", {})
        if task.get("abstract", False):
            continue
        print_t_name = "{:<40}".format(
            Colors.BOLD + t_name + Colors.RESET if info.show_colors else t_name)
        print(print_t_name, end='', flush=True)

        if t_meta.get("disabled", False):
            print("Skipped [disabled]")
            continue
        if info.skip_container_tests and "c_image" in task:
            print("Skipped [container]")
            continue
        output_gen_cmd = t_meta.get("output_gen_cmd", None)
        output_gen_cmd_rc = 0

        #  Check if this test needs to created the expected output file on the fly
        if output_gen_cmd:
            try:
                with open(INTERMEIDATE_EXPECTED, "r+") as f:
                    f.truncate()
                    output_gen_cmd_rc = subprocess.run(
                        output_gen_cmd, shell=True, stdout=f, stderr=f, text=True).returncode
            except OSError as e:
                output_gen_cmd_rc = 1
            finally:
                if output_gen_cmd_rc:
                    raise TaskTestException(
                        f"Error running expected output generation command for task '{t_name}'")
        run_task_cmd = "{} {} {}".format(base_cmd, t_name, t_meta.get("args", ""))
        run_task_cmd = shlex.split(run_task_cmd)
        try:
            if info.diff:
                with open(f"{OUTPUT_DIR}/{t_name}.out", "w") as f:
                    p = subprocess.Popen(run_task_cmd, stderr=f, stdout=f)
            else:
                p = subprocess.Popen(run_task_cmd)
            cmd_rc = p.wait()

            allowed_rc = t_meta.get("allowed_rc", [0])
            if cmd_rc not in allowed_rc:
                rc = 1
                print(f"{FAILED_STR}, unallowed return code '{cmd_rc}' (allowed={allowed_rc})")
                subprocess.Popen(["tail", "/tmp/task_runner.log"]).wait()
                if info.stop_on_failure:
                    return 1
                continue
            if not info.diff:
                print(f"{OK_STR} (output not validated)")
                continue
            out_file = f"{OUTPUT_DIR}/{t_name}.out"
            if output_gen_cmd:
                expected_file = INTERMEIDATE_EXPECTED
            else:
                expected_file = f"{SCRIPT_DIR}/{t_name}.expected"
            diff_cmd = f"diff -u {expected_file} {out_file}"
            pr = subprocess.run(diff_cmd.split(), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, encoding='utf-8')
            if not pr.returncode and not pr.stdout:
                print(OK_STR)
                continue
            print(f"{FAILED_STR}, output mismatch")
            if not pr.stdout:
                print("No diff output to show")  # Should not happen
            else:
                print(pr.stdout)
            if info.stop_on_failure:
                return 1
            rc = 1
        except OSError as e:
            raise TaskTestException(f"Error occurred running task '{t_name}' - {e}")
        except KeyboardInterrupt:
            raise TaskTestException("User interrupt")
    return rc


if __name__ == "__main__":
    rc = 0
    args = parse_arguments()

    try:
        with open(LOG_FILE, "a") as f:
            f.truncate()
        os.chdir(SCRIPT_DIR)

        if not os.path.isdir(OUTPUT_DIR):
            os.mkdir(OUTPUT_DIR)
        info = TestRunInfo(args)
        rc = run_test_tasks(info)
    except (OSError, ValueError, TaskTestException) as e:
        print(e)
        rc = 1
    exit(rc)
