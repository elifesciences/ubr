#!/bin/bash
set -e
find . -type d -name "__pycache__" -delete
find . -type f -name "*.py[co]" -delete
pyflakes ubr/
pylint -E ubr/* 2> /dev/null
