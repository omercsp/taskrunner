#!/bin/bash
set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${SCRIPT_DIR} || abort "Failed to cd to ${SCRIPT_DIR}"

SCRIPT_REAL_DIR=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
source ${SCRIPT_REAL_DIR}/devel_common.inc.sh

test_name=$1

if [ -z "$test_name" ]; then
	echo "Usage: $0 <test_name>"
	exit 1
fi

test_out_dir=$(_get_test_dir ${OUT_BASE_DIR} ${test_name}) || abort ${test_out_dir}
expected_dir=${test_out_dir/${OUT_BASE_DIR}/${EXPECTED_BASE_DIR}}

if [[ -d ${expected_dir} ]]; then
	rm -rf ${expected_dir:?}
fi

mkdir -p ${expected_dir:?}

# shellcheck disable=SC2068
for f in ${OUTPUT_FILES[@]}; do
	[[ ! -f ${test_out_dir}/${f} ]] && continue
	cp -v ${test_out_dir}/${f} ${expected_dir}
done
