#!/usr/bin/env bash
# This script is an adapter for github actions. It isn't meant to be ran
# manually by users.

OS=$(uname -s)

opts="--no-colors"
[[ ${OS} != "Linux" ]] && opts+=" --no-containers"
tests/tr_test --no-colors ${opts}
