import argparse
import argcomplete
import os
import pathlib
import shutil
import json
import subprocess


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
TASKS_JSON_FILE = "tasks.json"
GLOBAL_TASKS_FILE = "{}/.config/{}".format(pathlib.Path.home(), TASKS_JSON_FILE)
GLOBAL_TASKS_FILE_BACK = "{}.back".format(GLOBAL_TASKS_FILE)
TEST_GLOBAL_TASKS_FILE = "{}/global_{}".format(SCRIPT_DIR, TASKS_JSON_FILE)
LOG_FILE = "/tmp/task_runner.log"
OUTPUT_DIR = "{}/output".format(SCRIPT_DIR)
INTERMEIDATE_EXPECTED = "{}/intermediate.expected".format(SCRIPT_DIR)


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
    parser.add_argument('task', nargs='*', metavar='TASKS', help='set task')
    argcomplete.autocomplete(parser, always_complete_options=False)
    return parser.parse_args()


def read_tasks() -> dict:
    file_path = "{}/{}".format(SCRIPT_DIR, TASKS_JSON_FILE)
    try:
        data: dict = json.load(open(file_path, 'r'))
        return data["tasks"]
    except (IOError, TypeError, ValueError, KeyError) as e:
        raise TaskTestException("Error parsing {} - {}".format(file_path, e))


def run_test_tasks(tasks: dict, diff_output: bool, stop_on_failure: bool,
                   tasks_list: list[str], show_colors: bool, skip_container_tasks: bool) -> int:
    class Colors(object):
        BOLD = '\033[1m'
        GREEN = '\033[32m'
        ERROR = '\033[31m'
        RESET = '\033[m'
    if show_colors:
        OK_STR = Colors.GREEN + "OK" + Colors.RESET
        FAILED_STR = Colors.ERROR + "Failed" + Colors.RESET
    else:
        OK_STR = "OK"
        FAILED_STR = "Failed"

    if not tasks_list:
        tasks_list = list(tasks.keys())
    base_cmd = "{}/../task --log_file={} run".format(SCRIPT_DIR, LOG_FILE)
    rc = 0
    for t_name in tasks_list:
        task = tasks[t_name]
        t_meta = task.get("meta", {})
        #  Abstract tasks are never ran, and shouldn't be even considered to be ran. Usually used
        #  for inheritance and so.
        if t_meta.get("abstract", False):
            continue
        print_t_name = "{:<40}".format(Colors.BOLD + t_name + Colors.RESET if show_colors else t_name)
        print(print_t_name, end='')

        if t_meta.get("disabled", False):
            print("Skipped [disabled]")
            continue
        if skip_container_tasks and "c_image" in task:
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
                        "Error running expected outout generation command for task '{}'".format(t_name))

        if diff_output:
            run_task_cmd = "{} {} &> {}/{}.out".format(base_cmd, t_name, OUTPUT_DIR, t_name)
        else:
            run_task_cmd = "{} {}".format(base_cmd, t_name)
        try:
            cmd_rc = subprocess.Popen(run_task_cmd, shell=True).wait()
            should_fail = t_meta.get("should_fail", False)
            if (cmd_rc != 0 and not should_fail) or (cmd_rc == 0 and should_fail):
                rc = 1
                print("{}, unallowed exit (expected t)".format(FAILED_STR, rc), end=' ')
                if cmd_rc == 0:
                    print("task expected to succeed, but failed")
                if cmd_rc == 1:
                    print("task expected to fail, but succeded")
                if stop_on_failure:
                    return 1
                continue
            if not diff_output:
                print("{} (output not validated)".format(OK_STR))
                continue
            out_file = "{}/{}.out".format(OUTPUT_DIR, t_name)
            if output_gen_cmd:
                expected_file = INTERMEIDATE_EXPECTED
            else:
                expected_file = "{}/{}.expected".format(SCRIPT_DIR, t_name)
            diff_cmd = "diff -u {} {}".format(expected_file, out_file)
            pr = subprocess.run(diff_cmd.split(), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
            if not pr.returncode and not pr.stdout:
                print(OK_STR)
                continue
            print("{}, output missmatch".format(FAILED_STR, rc))
            if not pr.stdout:
                print("No diff output to show")  # Should not happen
            else:
                print(pr.stdout)
            if stop_on_failure:
                return 1
            rc = 1
        except OSError as e:
            raise TaskTestException("Error occurred running task '{}' - {}".format(t_name, e))
        except KeyboardInterrupt:
            raise TaskTestException("User interrupt")
    return rc


def init():
    try:
        with open(LOG_FILE, "a") as f:
            f.truncate()
        os.chdir(SCRIPT_DIR)

        if os.path.exists(GLOBAL_TASKS_FILE):
            shutil.copy(GLOBAL_TASKS_FILE, GLOBAL_TASKS_FILE_BACK)
        shutil.copy(TEST_GLOBAL_TASKS_FILE, GLOBAL_TASKS_FILE)
        if not os.path.isdir(OUTPUT_DIR):
            os.mkdir(OUTPUT_DIR)
    except (OSError, ValueError) as e:
        raise TaskTestException(str(e))


def fini():
    try:
        if os.path.exists(GLOBAL_TASKS_FILE):
            os.unlink(GLOBAL_TASKS_FILE)
        if os.path.exists(GLOBAL_TASKS_FILE_BACK):
            shutil.move(GLOBAL_TASKS_FILE_BACK, GLOBAL_TASKS_FILE)
    except Exception as e:
        print(e)
        print("Error occured during finalization of the script. Global tasks file might be wrong")


if __name__ == "__main__":
    rc = 0
    args = parse_arguments()

    try:
        init()
        tasks = read_tasks()
        rc = run_test_tasks(tasks, not args.no_diff, args.stop_on_failure,
                            args.task, not args.no_colors, args.no_containers)
    except TaskTestException as e:
        print(e)
        rc = 1
    finally:
        fini()
    exit(rc)
