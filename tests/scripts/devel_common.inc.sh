#!/bin/bash

# shellcheck disable=SC2034
EXPECTED_BASE_DIR=xeet.expected
OUT_BASE_DIR=xeet.out
OUTPUT_FILES="stdout stderr"

echoerr()
{
    echo "$@" 1>&2;
}
warn()
{
	local args="$*"

	# print warning in yellow
	echo -e "\033[33m${args}033[0m"
}
abort()
{
	echoerr Aborting: "$*"
	exit 1
}

_get_test_dir()
{
	local base_dir=$1
	local test_name=$2

	if [[ -d ${base_dir}/${test_name} ]]; then
		echo ${base_dir}/${test_name}
	else
		readarray -t test_directories < <(find ${base_dir} -name "${test_name}*" -type d -printf "%f\n")
		if [[ ${#test_directories[@]} -eq 0 ]]; then
			echo "No directory found for test ${test_name} in ${base_dir}"
			return 1
		fi

		if [[ ${#test_directories[@]} -gt 1 ]]; then
			echo "Multiple directories found for test ${test_name} in ${base_dir}"
			return 1
		fi
		echo ${base_dir}/${test_directories[0]}
	fi
}
