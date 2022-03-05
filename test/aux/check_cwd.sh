#!/bin/bash

if [[ -z ${EXPECTED_PWD} ]]; then
	echo "No expected PWD was found"
	exit 1
fi

pwd=$(pwd)
if [[ ${pwd} != ${EXPECTED_PWD} ]]; then
	echo "PWD mismatch."
	echo "EXPECTED_PWD=${EXPECTED_PWD}"
	echo "Found=${pwd}"
	exit 1
fi

echo "Silence is golden"
exit 0
