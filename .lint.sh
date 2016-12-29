#!/bin/bash
set -e
pyflakes ubr/
pylint -E ubr/* 2> /dev/null
