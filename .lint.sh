#!/bin/bash
set -e

# order is important
find . -type f -name "*.py[co]" -delete
find . -type d -name "__pycache__" -delete

pyflakes ubr/
pylint -E ubr/*
