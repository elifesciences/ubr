#!/bin/bash
set -e

pyflakes ubr/

args="$@"
module=""
if [ ! -z "$args" ]; then
    module=".$args"
fi

if [ ! -e test-config ]; then
    cp example.config test-config
fi
set -a; source test-config; set +a;

green ubr"$module" --run-coverage --processes 1 -vv
