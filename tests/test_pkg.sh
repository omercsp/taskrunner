#!/bin/bash

PKG_NAME=pytaskrunner
TEST_PYPI=${TEST_PYPI:-0}
TR_TEST=tr_test.py

if [[ ${TASK_RUNNER_PKG_TEST_ENV} -ne 1 ]]; then
	echo "Script wasn't called from the package testing environment"
	echo
	exit 1
fi

if [[ ! -e ${TR_TEST} ]]; then
	echo "'${TR_TEST} can't be found in current directory"
	echo
	exit 1
fi

if [[ ${TEST_PYPI} -eq 1 ]]; then
	REPO_FLAGS="-i https://test.pypi.org/simple --extra-index-url https://pypi.org/simple/"
fi

pip install ${REPO_FLAGS} ${PKG_NAME}
python3 ${TR_TEST}  --no-containers --pkg
