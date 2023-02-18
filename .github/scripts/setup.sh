#!/usr/bin/env bash
# This script is an adapter for github actions. It isn't meant to be ran
# manually by users.
OS=$(uname -s)
echo ${OS}

[[ ${OS} == "Darwin" ]] && brew install coreutils

python -m pip install --upgrade pip
pip install -r requirements.txt
if [[ ${OS} == "Linux" ]]; then
	podman pull docker.io/rockylinux/rockylinux:8.5
	podman pull docker.io/library/ubuntu:20.04
fi

pip install -e .

