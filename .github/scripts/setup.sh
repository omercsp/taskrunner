#!/usr/bin/env bash
# This script is an adapter for github actions. It isn't meant to be ran
# manually by users.
OS=$(uname -s)
echo ${OS}

[[ ${OS} == "Darwin" ]] && brew install coreutils

python -m pip install --upgrade pip
if [[ ${OS} == "Linux" ]]; then
	podman pull docker.io/rockylinux/rockylinux:9.3
	podman pull docker.io/library/ubuntu:24.04
fi

pip install -e .[devel]

