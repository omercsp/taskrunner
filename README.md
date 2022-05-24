# What is this?
Taskrunner (henceforth, TR) allows users to run tasks with relation to the current working directory. Somewhat similar to VScode tasks, TR tasks are not bound to a specific platform and can be invoked from any anywhere. A trivial environment for TR is a shell console, but any environment with ability to run executables is suitable.

One can think of TR is as a commands repository for a directory or a way to enable dynamic PATH, where commands becomes available and unavailable according to the working directory.

TR was written as a successor to `runevn`, a tool I wrote for running containers commands in similar manner which was extremely popular between myself and a guy I knew from work. `runenv` is great for sparing the user from remembering container settings for a given command, but is limited for a single task, isn't built for tasks that aren't container based and has limited features.

# Why do I need it?
Assume working on a project in a directory `project-dir`, where a long and complicated command like: `my-command -vv --with-this-flags --and-this-flag=5 THIS_ARG AND_THIS_ARG` is needed. Remembering and repeating it can be be annoying and time consuming.

One could rely on history, but history browsing for the command can be as annoying as typing it. Besides, after a long period of time, it might not even be there, and if another user need this command, he need to figure it out by his own.

Using shell script is a possible solution - place the logic in a script like `my-task.sh` and run it instead. This would work, but now we need to remember `my-task.sh` and where it resides. Unless placed in the search PATH, it's not just a matter of of running `my-task` but `path/to/my-task`. And again, if a another user needs to run this command by herself, she has to have knowledge of this command in advance.

An alias approach can also be tried: Alias `my-command-alias` to our command. Again, this works but suffers from some drawbacks: you are either bound to have the `my-command` available in PATH or have the entire project pinned to a given directory. In addition, aliases are user level entities: Moving the project to a different machine will require redefining the alias there. And once again - we need to know and remember what aliases are relevant - there's no way to differentiate between project and global aliases.

The situation might get more complicated if other commands are needed as well - with other arguments, other working directories, maybe some environment variables, etc.

With TR, all these problems are solved. All that is required is a project level configuration file defining a task named `my-task` to run the horrible `my-command...` and the command is available all over the project hierarchy, to all users with access to the project. `task list` can be used to see what tasks are available and `task info` to understand what they are doing. Moving this project to another machine will provide all the tasks with it.

## Installation and requirements
TR is python based tool, verified for python 3.6 and above. It should work for any environment with compatible python support, however it is developed an maintained on Linux machines.

To install:
1. Clone the repository
2. Install the requirements using pip `pip3 install -r requirements.txt`
3. Make sure the executable file `task` is accessible from to the execution search path (i.e. $PATH and so)

## Basic configuration and usage
TR uses json configuration files (By default, named `.tasks.json`) to describe tasks. These tasks are available when the current work directory is anywhere in the directory hierarchy under the directory the configuration file was placed in - TR recursively looks for `.tasks.json` from the current working directory up to root.

Once set, use the following commands:

1. Running tasks - by running `task run <TASK>`
2. Getting info on a task - by running `task info <TASK>`
3. Listing available tasks  - by running `task list`

As implied, configuration files are json files. Each each task is a json object with a name and a list of commands to execute.

### Example - building projects
[_source code projects is used in the following examples, but any sort of task is valid - `scp` some files, starting a service through `systemctl`, open a video with `vlc`, etc_]:

Assume a `cmake` based project  located in a directory named `cmake-project` with lots of sub directories. It might look something like this:

```bash
user@host $ tree cmake-project
.
├── build
├── subdir0
├── subdir1
│   └── subdir3
│       └── subdir4
└── subdir5
    └── subdir6
```

Often running basic `cmake` commands in such environments requires:

1. Entering the project's `build` directory
2. Running `cmake ..`

Not very complicated, but can get tedious when actively developing cmake files all over the tree. By adding the following `.tasks.json` file into `cmake-project` directory, rerunning the relevant cmake command becomes trivial one-liner:
```json
{
	"version": {
		"major": 4,
		"minor": 0
	},
	"tasks": {
		"cmake": {
			"short_desc": "Run cmake",
			"description": "Run 'cmake ..' for the cmake-project",
			"commands": ["cmake .."],
			"cwd": "{{taskRoot}}/build"
		}
	}
}
```
- version refers to the configuration file version number.
- The tasks section defines our tasks. Inside a single tasks is defined, name `cmake`.
  - `short_desc` and `description` are for documentation and self- explanatory.
  - `commands` sets a list of commands for this task to execute. In this case, a single `cmake ..` command is set.
  - `cwd` sets the working directory for this task. Its commands are executed with this setting value as their working directory. The `{{taskRoot}}` an automatic variable with the value of the location of the configuration file. Using it in `cwd` allows moving the project around without the need to update it. In our case, if the configuration file is placed in `cmake-project` root, say, `/home/user/projects/cmake-project`, the expanded value is  `/home/user/projects/cmake-project/build`.

**Running `task run cmake` from _anywhere_ under `cmake-project` will run the `cmake ..` with  `cmake-project/build` as the working directory**.

To list the available tasks, run `task list`:
```
user@host $ task list
Name                    Flags Description
----                    ----- -----------
cmake                         Run cmake

```

And for the task full details, run `task info  cmake`, an a `-x` flag values expansion; in our case, the workgin directory:
```
user@host $ task info -x cmake
Task name:              cmake
Short description:      Run cmake
Description:            Run 'cmake ..' for the cmake-project
Hidden                  No
Use shell:              No
Working directory:      /home/user/projects/cmake-project/build
Command:                cmake ..
```

Now lets assume there's a need to occasionally run another task, similar to the one already defined. For example, with some `cmake` definition like `-DSOMEVAR=somevalue`. And another task that actually builds the project with `cmake --build .. -j8` , both, like the first task, need to be invoked from the `build` directory (Again, if you don't care about `cmake` and building projects, don't worry about what the command does. Anything can be used here). Instead of remembering each command or placing these in shell scripts and then trying to remember where _they_ are, using TR tasks simplify the workflow:
```json
{
	"version": {
		"major": 4,
		"minor": 0
	},
	"tasks": {
		"cmake": {
			"short_desc": "Run cmake",
			"description": "Run 'cmake ..'' for the cmake-project",
			"commands": [
				"cmake .."
			],
			"cwd": "{{taskRoot}}/build"
		},
		"cmake-special": {
			"short_desc": "Run cmake with sepcial variable",
			"description": "Run 'cmake ..'' for the cmake-project, but with a spcial var defined",
			"commands": [
				"cmake -DSOMEVAR=somevalue .."
			],
			"cwd": "{{taskRoot}}/build"
		},
		"build": {
			"short_desc": "Build the project",
			"description": "Build the project using cmake's build command",
			"commands": [
				"cmake --build .."
			],
			"cwd": "{{taskRoot}}/build"
		}
	}
}
```

And now all commands are available, from any directory under `cmake-project`.
```bash
user@host $ task list
Name                    Flags Description
----                    ----- -----------
cmake                         Run cmake
cmake-special                 Run cmake with sepcial variable
build                         Build the project

user@host $ task info build
Task name:              build
Short description:      Build the project
Description:            Build the project using cmake's build command
Hidden                  No
Use shell:              No
Working directory:      /home/user/projects/cmake-project/build
Command:                cmake --build ..

user@host $ task run build
...
```

The above example can be further simplified by using variables and inheritance.

#### Multiple projects - same semantics, different details
Extending the example above, assume multiple projects, each with its own way of doing things. Let's say (based on true events), that other than the notorious `cmake-project` we have 2 additional projects named `make-project` and `scons-project` (and `ninja-project` and `meson` project etc...).

```bash
user@host $ tree projects
projects
├── cmake-project
├── make-project
└── scons-project
```
As these new projects name imply, these are `make` and `scons` project so building them is quite different than our old `cmake-project`, yet still we want to 'build' each one, but each has its own build system and details. We can try to remember each build command by our own and make sure we are in the correct project, or we can use TR: After adding a tasks file on each of these projects root directories each with its own `build` task, (like the `build` task exampled for `cmake-project`) the user can just run `task run build` in *any of these projects, and the correct build command will be invoked*. If her environment is consistent, she might add an alias like (Bash style) `alias build='task run build'` for even easier build - and whenever inside any of the source projects directories, running `build` invokes the correct command for for the current project.

## Advanced usage
This section will describe some of advanced configuration and usage topics. For a detailed list of all configuration settings, refer to the [configuration documentation](settings.md)

### Variables
A user can set her own variables that can be used through out the configuration. These variables are set in the `variables` object in the top level of the configuration file. A variable `D` is evaluated to strings, which can be referred to as `{{D}}` in most of the task properties. Can be useful when using the same value multiple times.  Definitions can be used in commands, environment variables, container names, container volumes, etc.
```json
{
	"version": {
		"major": 4,
		"minor": 0
	},
	"variables": {
		"ENV_NAME": "my_env_name",
		"ENV_VALUE": "my_env_value"
	},
	"tasks": {
		"task1": {
			"env": {
				"{{ENV_NAME}}": "{{ENV_VALUE}}"
			},
			"commands": [
				"printenv {{ENV_NAME}}"
			]
		}
	}
}
```

#### Auto variables
Regardless of the user defined variables, TR automatically defines the following variables:
1. `{{cwd}}` - for the current working directory. Note the `{{cwd}}` autodef refers to the working directory of the `task` executable, not the working directory set for tasks' commands.
2. `{{taskRoot}}` - for the path of the directory the found configuration file was found. This is helpful when a task needs to refer to a directory relatively to the project (see perilous examples for it usage).

*TR auto variables override any user variable*. So avoid setting variables with reserved names, as they will be overridden.

#### Environment variables
Environment variables can be referred with `{{$VAR}}`, where `VAR` is the variable name.

### Container based tasks
TR includes special support for running tasks inside a container. The main container setting is `c_image` which defines which image to use for the container. The following task runs `make` inside a container with a volume, CWD set, tty allocated, in interactive mode and wrapped in a `/usr/bin/sh -c`:
```json
"build": {
	"short_desc": "Build",
	"c_image": "localhost/media-builder:latest",
	"c_volumes": [
		"{cwd}:{cwd}"
	],
	"c_tty": true,
	"c_interactive": true,
	"c_shell": true,
	"c_cwd": "{{taskRoot}}"
	"commands": ["ls -l"],
},
```
The actual command the task invokes is `/usr/bin/docker -i -t --rm -w {{taskRoot}} -v {{cwd}}:{{cwd}} localhost/media-builder:laters /usr/bin/sh -c "ls -l"`.

Container support is synthetic sugar, and putting the complete container command as a `commands` entry instead of setting a task container settings is completely valid, but as it usually much easier let TR handle these settings for you.

For a detailed list of all container configuration settings, refer to the [configuration documentation](settings.md).

### Inheritance
A task might inherit another task settings by using the `base` settings. If task `a` inherits task `b`, all of `b`'s settings are inherited. Any setting that is redefined in task `a` will override whatever is defined in `b`.  The following example demonstrates how to utilize task inheritance for creating multiple tasks with similar characteristics that differ in a small details (working directory):

```json
"base-task": {
	"hidden": true,
	"commands": ["very_complicated command --with --lots=of --flags and arguments"],
	"env": {
		"and": "some",
		"environment": "variables"
	}
},
"task-1" {
	"base": "base-task",
	"cwd": "/opt/task-1_dir"
},
"task-2" {
	"base": "base-task",
	"cwd": "/opt/task-2_dir"
}
```

### Configuration files inclusion
Every configuration file can include multiple files using global `include` include setting. Global settings, variables and tasks are all included and overridden if exist in a following include file, and finally in the original configuration file.

A special file located in `${HOME}/.config/tasks.json` is always included if it exists. This behavior can be disabled by setting `use_default_include` to `false`.

### Passing command line arguments to commands
Command line arguments are transferred to a task run with the `--` convention: text written after the 'dash dash' token is transferred as arguments. This isn't passed to the commands automatically. In order for a command to use CLI arguments, it must be explicitly defined with the `{{cliArgs}}` variable. The fine grain control of which commands and where inside the command the CLI arguments are used. In fact, arguments are translates to a TR variable, so the variable `{{cliArgs}}` can be used in every setting with variables support.
Running `task run ls -- -l somefile.txt` in the following task will run `ls -l somefile.txt`:
```json
"ls": {
	"commands": ["ls {{cliArgs}}"],
	"short_desc": "Clean build"
}
```

## TR CLI options
TR allows overriding almost any configuration setting using the CLI. These should be avoided unless used for debugging a task, or tweaking it temporarily. For example, if one wants to run a task but just tweak the command it runs (and retain all other settings like container settings, environment variable, etc.), running `task run -c "my new command" <TASK>` will do the trick.

Run `task -h` and `task <CMD> -h` for the full list of CLI options.

## Bash completion
TR uses `argcomplete` for bash auto complete. See `argcomplete` documentation for more details.

## Logging
TR Logging can be enabled with the `--log_file <FILE>` CLI option. Use `-v` to increase its verbosity.

# Status
While tested and works, TR is still a work in progress. Breaking changes are expected. Version and schema validations will issue error messages if incompatibility is detected.
