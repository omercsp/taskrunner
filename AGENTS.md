# AGENTS.md — AI Agent Guide to Taskrunner (pytaskrunner)

This document provides a comprehensive overview of the `taskrunner` repository for AI agents. It details the architecture, code components, configuration mechanics, testing methodology, and development guidelines necessary to safely navigate, maintain, and enhance the codebase.

---

## 1. Project Overview & Purpose

- **Package Name**: `pytaskrunner`
- **CLI Executable**: `task` (entry point: `tr.__main__:main`)
- **Language**: Python (>= 3.10, < 4.0)
- **Primary Dependencies**: `pydantic>=2.8`, `PyYAML>=6.0.2,<7.0`, `argcomplete>=2.0.0`, `setuptools>=72`
- **Dev Dependencies**: `xeet==0.7.1`

`taskrunner` (abbreviated **TR**) is a CLI tool for managing and executing directory-scoped shell tasks. Similar to task runners embedded in IDEs (like VS Code tasks), TR operates independent of specific IDEs or platforms. It treats directories as task repositories, enabling a dynamic set of commands that become available or unavailable based on the current working directory.

### Core Capabilities
- **Hierarchical Config Discovery**: Searches upwards from the current working directory to the filesystem root for configuration files (`.tasks.yaml`, `tasks.yaml`, `.tasks.json`, `tasks.json`), with fallback to user home directory (`~/.config/`).
- **Variable Expansion**: Multi-level string variable interpolation (`{{var}}`), environment variables (`{{$ENV}}`), and built-in system variables (`{{taskRoot}}`, `{{cwd}}`, `{{cliArgs}}`).
- **Task Inheritance**: Tasks can inherit properties from base tasks (`base: <parent>`), with configurable command inheritance strategies (`base_cmds: default | before | after | ignore`) and granular control over inheriting env vars, task variables, and container volumes.
- **Container Execution**: First-class support for executing tasks inside containers (via `docker` or `podman`), generating `run` or `exec` CLI invocations with volume mounts, environment variables, working directories, and interactive TTY flags.
- **Config Inclusions & Suppression**: Multiple configuration files can be included recursively; tasks can be suppressed, marked `hidden`, or marked `abstract` (template-only).
- **Introspection & Schema Dumping**: Commands to inspect (`task info`), dump configurations (`task dump`, `task dump_config`), and export JSON schemas (`task dump_schema`).

---

## 2. Repository Layout

```
taskrunner/
├── .github/
│   ├── workflows/
│   │   ├── test.yml                   # CI test pipeline (Python 3.10-3.12 on Linux & macOS)
│   │   └── test-with-package.yml      # Workflow testing installed wheel package
│   └── scripts/
│       ├── setup.sh                   # CI environment setup (pulls container images on Linux)
│       └── run_test.sh                # CI test runner executing xeet
├── pyproject.toml                     # Project packaging, metadata, dependencies, scripts
├── requirements.txt                   # Flat runtime dependencies
├── task                               # Shell launcher wrapper with automatic venv activation
├── .tasks.yaml                        # Self-hosting taskrunner config (test, build, upload tasks)
├── README.md                          # User documentation and examples
├── settings.md                        # Reference manual for all global and task settings
├── schemas/                           # JSON Schema specifications for config validation
│   ├── taskrunner_v0.7.json
│   ├── taskrunner_v0.9.json
│   └── taskrunner_v0.11.json
├── src/
│   └── tr/                            # Main Python package
│       ├── __init__.py                # Package version resolution via importlib.metadata
│       ├── __main__.py                # CLI interface, argument parser, argcomplete, main entry
│       ├── actions.py                 # Subcommand implementations (run, list, info, dump, etc.)
│       ├── config.py                  # Config discovery, YAML/JSON parsing, Pydantic validation, inheritance
│       ├── Task.py                    # Runtime Task class, expansion, container/host execution
│       ├── common.py                  # StringVarExpander, TaskException, dict helpers, error formatting
│       └── logTools.py                # Logging system with frame inspection and raw/formatted modes
└── tests/                             # Test suite managed via xeet
    ├── xeet.yaml                      # Test matrix and configuration for xeet runner
    ├── tasks.yaml                     # Primary test task definitions
    ├── base_tasks_a.json              # Include fixture A
    ├── base_tasks_b.json              # Include fixture B
    ├── runtests                       # Development test launcher
    ├── run_pkg_tests                  # Packaged wheel test runner (creates fresh venv)
    ├── diff_test_output.sh            # Diff utility against golden files
    ├── update_test_output.sh          # Helper to update golden expected outputs
    ├── for_list_test/                 # Fixtures for task list testing
    ├── volumes/                       # Directory fixtures for container volume mount tests
    ├── scripts/                       # Output comparison scripts used by xeet
    └── xeet.expected/                 # Golden stdout/stderr outputs per test case
```

---

## 3. Architecture & Code Components

### `tr.__main__` (CLI Layer)
- Parses CLI arguments using `argparse`. Subcommands:
  - `run`: Executes a task. Accepts overrides for commands (`-c`), working directory (`--cwd`), shell mode (`--shell`, `--shell-path`), env vars (`--env`), container settings (`--c-image`, `--c-volume`, `--c-tool`, etc.), and variables (`-V`).
  - `list`: Lists available tasks with name, flags (`*` for default, `A` for abstract, `H` for hidden), and short description.
  - `info`: Displays full task details. Supports `-x` / `--expand` to show values after variable substitution.
  - `dump`: Dumps task configuration in YAML or JSON (`-i` resolves inheritance/inclusions).
  - `dump_config`: Dumps the full resolved configuration tree.
  - `dump_schema`: Dumps JSON schemas generated by Pydantic (`-t all | config | task`).
- Argument separation: sys.argv is split at `--`. Any arguments following `--` are joined as a string and mapped to `AutoVarsKeys.TASK_CLI_ARGS` (`cliArgs`).
- Exit Codes: `0` on success, `255` on `TaskException`, or the child process return code on command failure.
- Auto-completion: Integrates `argcomplete.autocomplete` with dynamic task name completion from `Config(None).visible_tasks()`.

### `tr.config` (Configuration & Validation Layer)
- **File Discovery**: `_find_default_config_file()` searches current directory and parents upwards to `/` for `.tasks.yaml`, `tasks.yaml`, `.tasks.json`, `tasks.json`. If none match, checks `~/.config/`. Overridable with `-C` / `--conf`.
- **System / Constant Variables**: Populated early before full file parsing:
  - `cwd`: Current working directory when TR was invoked.
  - `taskRoot`: Directory where the active config file resides.
  - `cliArgs`: Joined string of arguments passed after `--`.
- **Pydantic Validation**:
  - `ConfigFileModel`: Validates root config with `extra='forbid'`. Keys: `$schema`, `include`, `use_default_include`, `tasks`, `suppress`, `variables`, `default_task`, `default_shell_path`, `default_container_tool`, `default_container_shell_path`.
  - `TaskModel`: Validates task entries with `extra='forbid'`. Supports aliases for descriptions and base commands (`base_cmds` / `base_commands`, `short_desc` / `short_description`, `long_desc` / `description`).
- **File Inclusions (`include`)**:
  - Included files are recursively resolved in order.
  - Loop detection prevents cyclic inclusions (`Include loop detected`).
  - Top-level config includes `~/.config/tasks.json` if `use_default_include: true` (the default).
- **Inheritance Resolution (`Config.task_desc`)**:
  - Resolves `base` inheritance hierarchy recursively with cycle detection (`Inheritance loop detected`).
  - Merges `variables`, `env`, `c_env` (parent updated by child if inheritance flags are true).
  - Merges `c_volumes` (parent appended to child if `c_inherit_volumes` is true).
  - Merges `commands` based on `base_cmds`:
    - `default`: Uses child commands if defined; otherwise uses base commands.
    - `before`: Runs base commands before child commands.
    - `after`: Runs child commands before base commands.
    - `ignore`: Omits base commands regardless of child commands.
  - Task name resolution allows unique prefix matching (e.g. `task run bui` matches `build`).

### `tr.Task` (Runtime & Execution Layer)
- **Initialization**: Instantiates a runtime `Task` from the validated `TaskModel` and defaults.
- **Variable Expansion (`expand()`)**:
  - Instantiates `StringVarExpander(self.vars_map)`.
  - Expands `env`, `cwd`, `commands`, `c_cwd`, `c_image`, `c_env`, and `c_volumes`.
- **Command Synthesis**:
  - Non-container commands: If `shell: true`, passed as single string to shell; otherwise split into argv using `shlex.split()`.
  - Container commands (`_container_cmd_arr()`): Synthesizes container CLI invocation (`docker` or `podman`).
    - Prepends `sudo` if `c_sudo: true`.
    - Chooses subcommand: `exec` if `c_exec: true`, else `run`.
    - Adds `-w <c_cwd>`, `-i` (interactive), `-t` (tty), `--rm` (if `c_rm` and not `c_exec`), `-v <volume>` entries, `-e <k=v>` entries, and `c_flags`.
    - Wraps command in `<c_shell_path> -c "<cmd>"` if `c_shell: true`.
- **Execution (`_run_cmd()`)**:
  - Uses `subprocess.Popen(shell=self.shell, executable=self.shell_path, env=env, cwd=self.cwd)`.
  - Environment merging: Uses `os.environ` merged with task `env` if `env_inherit: true`; otherwise uses task `env` exclusively.
  - Signal handling: Intercepts `KeyboardInterrupt`, sends `SIGINT` to child process, and raises `TaskException("User interrupt")`.
  - Multiple commands: Iterates through commands. If a command fails and `stop_on_error: true`, execution terminates immediately. If `stop_on_error: false`, subsequent commands continue running, returning the first non-zero return code.

### `tr.actions` (Action Execution & Output Presentation)
- `run_task`: Applies CLI arg overrides (`args_update`), expands variables, optionally prints task summary (`-s`), and calls `task.run()`.
- `list_tasks`: Formats task list output in columns (`Name`, `Flags`, `Description`), handling truncation and error display for malformed tasks.
- `show_task_info`: Formatted key-value printout of all task properties, container options, environment variables, and commands.
- `dump_task`, `dump_config`, `dump_schema`: Serializes data into YAML or JSON, supporting alphabetical sorting via `sort_dict()`.

### `tr.common` (Utilities & Variable Expander)
- `StringVarExpander`:
  - Regex matcher for `{{\S*?}}`.
  - Variable precedence: System constants (`cwd`, `taskRoot`, `cliArgs`) > Task variables > Global variables.
  - Environment variable lookup: `{{$VAR}}` accesses `os.getenv("VAR", "")`.
  - Recursive evaluation: Resolves variables defined in terms of other variables (e.g. `a: "{{b}}"`). Detects recursion loops via `expansion_stack`.
  - Rejects non-scalar expansions (lists/dicts).
- `TaskException`: Custom exception type used throughout TR for predictable error handling without uncaught stack traces.
- `dump_dict` / `DictDumpFmt`: Helpers for formatted YAML/JSON dumping.
- `pydantic_errmsg`: Formats Pydantic validation errors into human-readable path strings.

### `tr.logTools` (Logging Infrastructure)
- Implements `TrLogging` wrapping Python's `logging` library.
- Formats:
  - Default: `L [filename:lineno] function_name................: message`
  - Raw: unformatted message string (used for clean data dumps and variable logging).
- Helpers: `info`, `verbose`, `warn`, `error`, `error_and_print`, `warn_and_print`, `start_raw_logging`, `stop_raw_logging`.
- Activated via `--log_file <FILE>` and `-v` CLI options.

---

## 4. Configuration Schema & Options Reference

Configurations can be defined in YAML or JSON.

### Global Configuration (`ConfigFileModel`)
| Field | Type | Default | Description |
|---|---|---|---|
| `$schema` | `string` | `null` | Path or URL to JSON schema for IDE validation |
| `include` | `list[str]` | `[]` | List of other configuration files to include |
| `use_default_include` | `bool` | `true` | Include `${HOME}/.config/tasks.json` if present |
| `tasks` | `dict[str, TaskModel]` | `{}` | Map of task definitions |
| `suppress` | `list[str]` | `[]` | Task names to suppress/disable from included files |
| `variables` | `dict[str, str]` | `{}` | Global variables available to all tasks |
| `default_task` | `str` | `null` | Task executed when `task run` is invoked with no task name |
| `default_shell_path` | `str` | `"/bin/sh"` | Fallback shell executable for host tasks |
| `default_container_tool` | `str` | `"/usr/bin/docker"` | Container engine executable (`docker` or `podman`) |
| `default_container_shell_path` | `str` | `"/bin/sh"` | Fallback shell executable inside containers |

### Task Configuration (`TaskModel`)
| Field | Type | Default | Description |
|---|---|---|---|
| `short_desc` / `short_description` | `str` | `null` | Max 75-character summary shown in `task list` |
| `long_desc` / `description` | `str` | `null` | Extended documentation shown in `task info` |
| `commands` | `list[str]` | `[]` | List of command strings to execute in sequence |
| `cwd` | `str` | `null` | Working directory for commands (supports `{{taskRoot}}`) |
| `shell` | `bool` | `false` | Run commands wrapped in a shell process |
| `shell_path` | `str` | `null` | Custom shell path (defaults to global `default_shell_path`) |
| `env` | `dict[str, str]` | `{}` | Environment variables set for task execution |
| `inherit_os_env` | `bool` | `true` | Inherit ambient OS environment variables |
| `stop_on_error` | `bool` | `true` | Halt execution on the first command that returns non-zero |
| `hidden` | `bool` | `false` | Hide task from default `task list` (visible with `-a`) |
| `abstract` | `bool` | `false` | Template-only task; cannot be run directly |
| `base` | `str` | `null` | Name of parent task to inherit settings from |
| `base_cmds` / `base_commands` | `enum` | `"default"` | Command inheritance: `default`, `before`, `after`, `ignore` |
| `inherit_env` | `bool` | `true` | Inherit environment variables from base task |
| `variables` | `dict[str, str]` | `{}` | Task-scoped variables (override global variables) |
| `inherit_variables` | `bool` | `true` | Inherit variables from base task |
| **Container Settings** | | | |
| `c_image` | `str` | `null` | Container image name (or container name/ID if `c_exec: true`) |
| `c_container_tool` | `str` | `null` | Override container tool for this task |
| `c_volumes` | `list[str]` | `[]` | Volume mounts in `HOST_DIR:CONTAINER_DIR` format |
| `c_inherit_volumes` | `bool` | `true` | Inherit volume mounts from base task |
| `c_interactive` | `bool` | `false` | Pass `-i` to container tool |
| `c_tty` | `bool` | `false` | Pass `-t` to container tool |
| `c_flags` | `str` | `null` | Extra raw flags passed verbatim to container tool |
| `c_exec` | `bool` | `false` | Use `exec` on running container instead of `run` |
| `c_remove` | `bool` | `true` | Pass `--rm` to container tool (ignored if `c_exec: true`) |
| `c_sudo` | `bool` | `false` | Run container tool with `sudo` |
| `c_shell` | `bool` | `false` | Wrap container command in `<c_shell_path> -c` |
| `c_shell_path` | `str` | `null` | Shell path inside container (defaults to global setting) |
| `c_env` | `dict[str, str]` | `{}` | Container environment variables (`-e KEY=VAL`) |
| `c_inherit_env` | `bool` | `true` | Inherit container environment variables from base task |
| `c_cwd` | `str` | `null` | Working directory inside container (`-w <c_cwd>`) |

---

## 5. Testing Framework & Verification

The repository relies on `xeet` (an external test harness) for its integration test suite.

### Test Structure
- **Definition File**: `tests/xeet.yaml` defines all test cases, inheritance templates, and allowed return codes.
- **Fixture Config**: `tests/tasks.yaml` defines the tasks executed during testing.
- **Golden Output Verification**:
  - Tests invoke TR commands and compare stdout and stderr against golden master files stored in `tests/xeet.expected/<test_name>/stdout` and `stderr`.
  - Comparison script: `tests/scripts/dflt_output_compare.sh` (sources `tests/scripts/common.inc.sh`).
- **Test Groups**:
  - `vars`: Variable expansion and override behaviors.
  - `cmds_inherit`: Command inheritance strategies (`before`, `after`, `ignore`, multi-depth).
  - `container`: Container tasks with Ubuntu 24.04 and Rocky Linux 9.3 (requires Podman/Docker).

### Running Tests
1. **Using taskrunner itself** (from repository root):
   ```bash
   ./task run test
   ```
2. **Direct test runner script**:
   ```bash
   tests/runtests
   ```
3. **Excluding container tests** (e.g. environments without Docker/Podman):
   ```bash
   tests/runtests -X container
   ```
4. **Testing installed package in clean virtualenv**:
   ```bash
   tests/run_pkg_tests
   ```

### Managing Test Outputs
- View test output diffs:
  ```bash
  tests/diff_test_output.sh <test_name>
  ```
- Inspect generated output files:
  ```bash
  tests/test_output.sh <test_name>
  ```
- Update golden expected outputs after deliberate behavior changes:
  ```bash
  tests/update_test_output.sh <test_name>
  ```

---

## 6. Developer & Agent Guidelines

When modifying this repository, AI agents must strictly follow these rules:

### Python Coding Standards
- **Style & Indentation**: Follow PEP 8 (4 spaces, snake_case for functions/variables, CamelCase for classes).
- **Line Length**: Max 100 characters per line (defined in `~/.config/pycodestyle`).
- **Linter Verification**: Run `pycodestyle src/tr/*.py` before finalizing changes. All changes must be clean.
- **Type Annotations**: Always include type hints for function signatures (parameters and return types).
- **Guard Clauses**: Check error conditions early and return/raise immediately to maintain flat scopes.
- **Imports**: Place imports at the top of the file, ordered logically. Avoid local/in-function imports.
- **Multi-Argument Alignment**: Align function parameters on continuation lines vertically under the first argument after the opening parenthesis.
- **Comments**: Use `#` for comments. Comment on *why*, not *what*. Never add commentary directed at users.

### Bash Script Standards
- Use `[[ ... ]]` instead of `[ ... ]` for conditional tests.
- Always use curly braces for variable expansion (e.g. `${VAR}`).
- Use `#!/usr/bin/env bash` for shebangs.
- Prefix script-private/internal functions with an underscore (e.g. `_my_func`).
- Place opening function braces on a new line:
  ```bash
  function_name()
  {
      # body
  }
  ```

### Git & Commit Guidelines
- Do not commit changes unless explicitly requested by the user.
- Leave modified files unstaged.
- If requested to commit, follow the repository's commit format:
  - Subject prefix: `<TOPIC>: <short description>` where `<TOPIC>` is typically `tr`, `tests`, `github`, or `build`.
  - Short description in all lower-case (except acronyms/proper names).
  - 50/72 rule: First line <= 50 characters, blank second line, body wrapped at 72 characters.
  - Focus message body on *why* the change was made, not a mechanical walk-through of the diff.
  - Include `Signed-off-by` trailer (`git commit -s`).

### Schema & Model Synchronization
- When modifying or adding configuration fields in `src/tr/config.py` (`ConfigFileModel` or `TaskModel`):
  1. Ensure `model_config = ConfigDict(extra='forbid')` remains intact.
  2. Maintain field validation aliases for backwards compatibility where appropriate.
  3. If configuration options are added or modified, update `settings.md` and generate/update schemas under `schemas/` (using `task dump_schema`).
  4. If CLI output or formatting changes, verify all affected tests in `tests/xeet.expected/` and update them using `tests/update_test_output.sh`.
