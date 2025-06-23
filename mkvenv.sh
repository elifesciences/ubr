#!/bin/bash
set -e

python=$(which python3 python | head -n 1)

py=${python##*/} # "python3" or "python"

if [[ "$(readlink venv/bin/$py)" != "$python"  ]]; then
    echo "venv/bin/$py is not symlinked to $python removing venv"
    rm -rf venv/*
fi

if [ -z "$python" ]; then
    echo "no usable python found, exiting"
    exit 1
fi

if [ ! -e "venv/bin/$py" ]; then
    echo "could not find venv/bin/$py, recreating venv"
    rm -rf venv
    $python -m venv venv
else
    echo "using $python"
fi
