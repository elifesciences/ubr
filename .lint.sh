#!/bin/bash
set -e
pylint -E *.py ubr/*.py ubr/tests/*.py
