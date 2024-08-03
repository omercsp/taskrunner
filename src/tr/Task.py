from tr.config import Config
from tr.logTools import info, warn, raw_msg, logging_enabled_for
from tr.common import TaskException, StringVarExpander
import logging
import os
import shlex
import subprocess
import signal


class Task(object):
    def _check_empty_setting(self, s, title) -> None:
        if len(s) > 0:
            return
        raise TaskException(f"Expanded {title} for task '{self.name}' is empty")

    def __init__(self, name: str, config: Config) -> None:
        super().__init__()
        info("Initializing task '{}'", name)
        self.name = name
        model = config.task_model(name, True)

        self.short_desc = model.short_desc
        self.long_desc = model.long_desc
        self.hidden = model.hidden
        self.stop_on_error = model.stop_on_error
        self.commands = model.commands
        self.cwd = model.cwd
        self.shell = model.shell
        if self.shell:
            if model.shell_path:
                self.shell_path = model.shell_path
            else:
                self.shell_path = config.default_shell_path
        else:
            self.shell_path = None
        self.env_inherit = model.inherit_os_env
        self.env = model.env
        self.abstract = model.abstract
        self.c_image = model.c_image if model.c_image else ""
        self.c_volumes = model.c_volumes
        self.c_interactive = model.c_interactive
        self.c_tty = model.c_tty
        self.c_flags = model.c_flags if model.c_flags else ""
        self.c_exec = model.c_exec
        self.c_rm = model.c_remove
        if model.c_container_tool:
            self.c_tool = model.c_container_tool
        else:
            self.c_tool = config.default_container_tool
        self.c_shell = model.c_shell
        if model.c_shell_path:
            self.c_shell_path = model.c_shell_path
        else:
            self.c_shell_path = config.default_container_shell_path
        self.c_cwd = model.c_cwd
        self.c_env = model.c_env
        self.c_sudo = model.c_sudo
        self.vars_map = model.variables
        self.expander = None

    def expand(self) -> None:
        if self.expander is not None:
            warn("Task '{}' is already expanded", self.name)
            return
        self.expander = StringVarExpander(self.vars_map)
        info(f"Expanding task '{self.name}'")
        self.env = {self.expander(k): self.expander(v) for k, v in self.env.items()}
        if self.cwd:
            self.cwd = self.expander(self.cwd)
        self.commands = [self.expander(c) for c in self.commands]

        if self.c_cwd:
            self.c_cwd = self.expander(self.c_cwd)
        if self.c_image:
            self.c_image = self.expander(self.c_image)
        self.c_env = {self.expander(k): self.expander(v) for k, v in self.c_env.items()}
        self.c_volumes = [self.expander(v) for v in self.c_volumes]

    def _simple_cmd_arr(self, cmd) -> list:
        info("Preparing simple command")
        if self.shell:
            return [cmd]
        try:
            return shlex.split(cmd)
        except ValueError as e:
            raise TaskException(f"Illegal command '{cmd}' for task '{self.name}' - {e}")

    def _container_cmd_arr(self, cmd) -> list[str]:
        info("Preparing container command")
        cmd_array: list[str] = ["sudo", self.c_tool] if self.c_sudo else [self.c_tool]
        cmd_array.append("exec" if self.c_exec else "run")
        if self.c_cwd:
            cmd_array += ["-w", self.c_cwd]
        if self.c_interactive:
            cmd_array.append("-i")
        if self.c_tty:
            cmd_array.append("-t")
        if not self.c_exec:
            if self.c_rm:
                cmd_array.append("--rm")
            for v in self.c_volumes:
                cmd_array += ["-v", v]

        for k, v in self.c_env.items():
            cmd_array += ["-e", f"{k}={v}"]
            info("Setting container environment variable will '{}={}'", k, v)

        cmd_array += self.c_flags.split()

        cmd_array.append(self.c_image)
        if self.c_shell and cmd is not None:
            cmd_array += [self.c_shell_path, "-c"]
        if cmd:
            cmd_array += [cmd]
        info("Command is {}", cmd_array)
        return cmd_array

    def _run_cmd(self, cmd: list[str], cmd_str: str) -> int:
        info("Running command (joined):")
        raw_msg(cmd_str)
        p = None
        if self.env_inherit:
            env = os.environ
            env.update(self.env)
        else:
            env = self.env
        try:
            p = subprocess.Popen(cmd, shell=self.shell,
                                 executable=self.shell_path, env=env, cwd=self.cwd)
            return p.wait()

        except (OSError, FileNotFoundError) as e:
            raise TaskException(f"Error occurred running command '{cmd_str}' - {e}")
        except KeyboardInterrupt:
            if p:
                p.send_signal(signal.SIGINT)
                p.wait()
            raise TaskException("User interrupt")

    def run(self) -> int:
        if self.expander is None:
            raise TaskException("Task must be expanded before run")  # Should never happen
        if self.abstract:
            raise TaskException("Can't run abstract tasks")
        if logging_enabled_for(logging.INFO):
            if self.cwd:
                info("Working directory will be set to '{}'", self.cwd)
            else:
                info("No working directory will be set")
            if self.env:
                info("Command Environment variables:")
                for k, v in self.env.items():
                    raw_msg(f"{k}={v}")

        if len(self.commands) == 0:
            if self.c_image:
                info("Running container's default command")
                return self._run_cmd(self._container_cmd_arr(None), "<CONTAINER_DEFAULT>")
            print(f"No commands defined for task '{self.name}'. Nothing to do.")
            return 0

        rc = 0
        for cmd in self.commands:
            info("Command is '{}'", cmd)
            cmd_arr = self._container_cmd_arr(cmd) if self.c_image else self._simple_cmd_arr(cmd)
            cmd_rc = self._run_cmd(cmd_arr, cmd)
            if cmd_rc == 0:
                continue
            info("Command had failed cmd_rc={}", cmd_rc)
            if self.stop_on_error:
                info("Stopping of first error")
                return cmd_rc
            if rc == 0:
                rc = cmd_rc
        return rc
