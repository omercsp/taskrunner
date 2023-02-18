from tr.schemas import *
from tr.common import *
import os
import pathlib
import json
from typing import Optional, Set
from argparse import Namespace as Args


_CONF_FILE_NAME = "tasks.json"
_DFLT_CONF_FILE_NAME = str(pathlib.Path.home()) + "/.config/" + _CONF_FILE_NAME


class Config(object):
    @staticmethod
    def _read_tasks_file(file_path: str) -> dict:
        try:
            data: dict = json.load(open(file_path, 'r'))
        except (IOError, TypeError, ValueError, TaskException) as e:
            raise TaskException(f"Error parsing {file_path} - {e}")
        return data


    def _read_configuration(self, file_path: str, read_files: set = set()) -> dict:
        conf = {}
        tasks = {}
        variables = {}
        info("Reading configuration file {}", file_path)
        orig_conf = Config._read_tasks_file(file_path)
        includes = orig_conf.get(GlobalKeys.Include, [])

        # Add the default configuration file to includes list but only for the original
        # configuration file, and the behavior isn't turned off (again, relevant ONLY to
        # original file)
        if len(read_files) == 0 and \
                file_path != _DFLT_CONF_FILE_NAME and \
                os.path.isfile(_DFLT_CONF_FILE_NAME) and \
                orig_conf.get(GlobalKeys.UseDfltInclude, True):
            includes.insert(0, _DFLT_CONF_FILE_NAME)

        info("Configuration file includes: {}", includes)
        read_files.add(file_path)
        expander = StringVarExpander()
        for f in includes:
            f = expander(f)
            if f in read_files:
                raise TaskException(f"Include loop detected - '{f}'")
            included_conf = self._read_configuration(f, read_files)
            tasks.update(included_conf[GlobalKeys.Tasks])
            variables.update(included_conf[GlobalKeys.Variables])
            conf.update(included_conf)
        read_files.remove(file_path)
        if GlobalKeys.Include in conf:
            conf.pop(GlobalKeys.Include)

        conf.update(orig_conf)
        tasks.update(orig_conf.get(GlobalKeys.Tasks, {}))
        for supressed_task in conf.get(GlobalKeys.Suppress, []):
            if supressed_task in tasks:
                info("Removing suppressed task {}", supressed_task)
                tasks.pop(supressed_task)
        conf[GlobalKeys.Tasks] = tasks
        variables.update(orig_conf.get(GlobalKeys.Variables, {}))
        conf[GlobalKeys.Variables] = variables
        return conf

    @staticmethod
    def _get_conf_file_path(cli_conf: Optional[str]) -> Optional[str]:
        if cli_conf:
            return cli_conf

        directory = os.getcwd()
        while True:
            conf_path = directory + "/." + _CONF_FILE_NAME
            if os.path.isfile(conf_path):
                return conf_path
            if directory == "/":
                break
            directory = os.path.dirname(directory)

        if os.path.isfile(_DFLT_CONF_FILE_NAME):
            return _DFLT_CONF_FILE_NAME
        return None

    def __init__(self, args: Optional[Args]) -> None:
        self.args: Args = args  # type: ignore
        conf_path = Config._get_conf_file_path(args.conf if args else None)

        #  Populate some variables early so they are available in
        const_vars = {}
        cwd = os.getcwd()
        const_vars[AutoVarsKeys.CWD] = cwd
        if conf_path:
            conf_dir_name = os.path.dirname(conf_path)
            if conf_dir_name:
                const_vars[AutoVarsKeys.TASK_ROOT] = os.path.dirname(conf_path)
        const_vars.setdefault(AutoVarsKeys.TASK_ROOT, cwd)
        if args and args.__contains__(AutoVarsKeys.TASK_CLI_ARGS):
            const_vars[AutoVarsKeys.TASK_CLI_ARGS] = " ".join(
                args.__getattribute__(AutoVarsKeys.TASK_CLI_ARGS))
        set_const_vars_map(const_vars)

        self.conf = {}
        if conf_path:
            self.conf = self._read_configuration(conf_path)
            validate_config_file_schema(self.conf)

        self.tasks = self.conf.get(GlobalKeys.Tasks, {})
        set_global_vars_map(self.conf.get(GlobalKeys.Variables, {}))

        if logging_enabled_for(logging.DEBUG):
            dump_defualt_vars()

    def default_task_name(self) -> Optional[str]:
        return self.setting(GlobalKeys.DfltTask)

    def default_container_tool(self) -> str:
        return self.setting(GlobalKeys.DfltContainerTool, default="/usr/bin/docker")

    def default_container_shell_path(self) -> str:
        return self.setting(GlobalKeys.DfltContainerShellPath, default="/usr/bin/sh")

    def default_shell_path(self) -> Optional[str]:
        return self.setting(GlobalKeys.DfltShellPath, None)

    def visible_tasks(self) -> typing.List[str]:
        tasks = set()
        for name, task in self.tasks.items():
            if not task.get(TaskKeys.Hidden, False):
                tasks.add(name)
        return list(tasks)

    #  Return anything. Types is forced by schema validations.
    def setting(self, path: str, default=None) -> typing.Any:
        return dict_value(self.conf, path, default=default)

    def _raw_task_obj(self, name: str) -> dict:
        try:
            return self.tasks[name]
        except KeyError:
            raise TaskException(f"No such task '{name}'")

    @staticmethod
    def _consolidate_commands(task_desc: dict) -> None:
            task_desc[TaskKeys.Commands] = \
               task_desc.get(TaskKeys.PreCommands, []) + \
               task_desc.get(TaskKeys.Commands, []) + \
               task_desc.get(TaskKeys.PostCommands, [])
            task_desc.pop(TaskKeys.PreCommands, None)
            task_desc.pop(TaskKeys.PostCommands, None)

    @staticmethod
    def update_task_desc(tgt_desc: dict, derived_desc:dict, merge: typing.Set[str]) -> None:
        for k, v in derived_desc.items():
            value_type = type(v)
            if k in merge and not (value_type is dict or value_type is list):
                raise TaskException(f"Unmergeable value '{k}' {type(v)}")

            if k in merge and k in tgt_desc:
                if value_type is dict:
                    if type(tgt_desc[k]) is not dict:
                        raise TaskException(f"Expecetd dictionary for key '{k}'")
                    tgt_desc[k].update(v)
                    continue
                if value_type is list:
                    if type(tgt_desc[k]) is not list:
                        raise TaskException(f"Expecetd list for key '{k}'")
                    tgt_desc[k] += v
                    continue
            tgt_desc[k] = v


    def _task_desc(self, name: str, included_list: set) -> dict:
        if name in included_list:
            raise TaskException(f"Ineritance loop detected for task '{name}'")

        included_list.add(name)
        derived_desc = self._raw_task_obj(name)

        ret_task_name = derived_desc.get(TaskKeys.Base, None)
        if ret_task_name is None or not ret_task_name.strip():
            Config._consolidate_commands(derived_desc)
            return derived_desc

        merge = set()
        if derived_desc.get(TaskKeys.InheritVariables, True):
            merge.add(TaskKeys.Variables)
        if derived_desc.get(TaskKeys.InheritEnv, True):
            merge.add(TaskKeys.Env)
        if derived_desc.get(TaskKeys.CInheritEnv, True):
            merge.add(TaskKeys.CEnv)
        if derived_desc.get(TaskKeys.CInheritVolumes, True):
            merge.add(TaskKeys.CVolumes)

        # We about to modify the included object, so deep copy it
        ret_desc = self._task_desc(ret_task_name, included_list=included_list).copy()
        for k in [TaskKeys.Hidden, TaskKeys.Abstract, TaskKeys.InheritEnv, TaskKeys.InheritVariables,
                  TaskKeys.CInheritEnv, TaskKeys.CInheritVolumes]:
            ret_desc.pop(k, None)
        Config.update_task_desc(ret_desc, derived_desc, merge)

        Config._consolidate_commands(ret_desc)
        return ret_desc

    def get_task_desc(self, name: str, includes: bool) -> typing.Dict[str, typing.Any]:
        verbose("Task '{}' requested, with_inclusions={}", name, includes)
        if includes:
            return self._task_desc(name, set())
        else:
            return self._raw_task_obj(name)
