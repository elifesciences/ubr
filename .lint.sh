#!/bin/bash
set -e
pylint -E *.py ubr/*.py ubt/tests/*.py
