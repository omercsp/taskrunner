#!/usr/bin/env bash
# This script is an adapter for github actions. It isn't meant to be ran
# manually by users.

OS=$(uname -s)

opts=""
[[ ${OS} != "Linux" ]] && opts+="-X container"

export USE_VENV=0
cd ${GITHUB_WORKSPACE}/tests || exit 1

xeet --no-colors run -c xeet.json ${opts}
