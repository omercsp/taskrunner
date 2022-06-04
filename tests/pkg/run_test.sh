#!/bin/bash

PKG_NAME=pytaskrunner
TEST_PYPI=${TEST_PYPI:-0}
if [[ ${TASK_RUNNER_PKG_TEST_ENV} -ne 1 ]]; then
	echo "Script wasn't called from the package testing environment"
	echo
	exit 1
fi

if [[ ${TEST_PYPI} -eq 1 ]]; then
	REPO_FLAGS="-i https://test.pypi.org/simple --extra-index-url https://pypi.org/simple/"
fi

pip install ${REPO_FLAGS} ${PKG_NAME}
python3 tr_test.py  --no-containers --pkg
