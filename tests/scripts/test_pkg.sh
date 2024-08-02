#!/bin/bash
set -e
[[ -n ${VIRTUAL_ENV} ]] && deactivate

TEST_PYPI=${TEST_PYPI:-0}

# Stupid Apple
if [[ ${OSTYPE} == 'darwin'* ]]; then
	READLINK="greadlink"
else
	READLINK="readlink"
fi

SCRIPT_FILE="$(${READLINK} -f ${BASH_SOURCE[0]})"
SCRIPT_DIR="$(dirname $SCRIPT_FILE)"
venv_dir=""

_abort()
{
	echo "$@"
	echo
	exit 1
}

_build_pkg_venv()
{
	local repo_flags=""

	[[ -n ${VENV_ACTIVATE} ]] && \
	    _abort "Virtual environment is activate. Deactivate and run again"

	if [[ ${TEST_PYPI} -eq 1 ]]; then
	    repo_flags="-i https://test.pypi.org/simple --extra-index-url https://pypi.org/simple/"
	fi
	venv_dir=$(mktemp -d)
	echo "Creating venv at ${venv_dir}"
	python -m venv ${venv_dir}
	source ${venv_dir}/bin/activate
        pip install --upgrade pip
        pip install xeet

	pip install ${repo_flags} pytaskrunner
}

_fini_pkg_env()
{
    deactivate
    [[ -n ${venv_dir} && -d ${venv_dir} ]] && rm -rf ${venv_dir}
}

_build_pkg_venv
which xeet
which task
cd ${SCRIPT_DIR:?}/.. || _abort "Can't change to tests directory"

xeet run --log-file=xeet.log -c xeet.json
ret=$?
_fini_pkg_env

exit ${ret}
