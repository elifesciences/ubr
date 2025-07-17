#!/bin/bash
# calls the command line interface to the universal backup/restore script
# assumes script is being run from directory it lives in
set -e

mise exec -- ./install.sh > /dev/null

# usage: ubr <backup|restore> <dir|s3> [target] [path]
mise exec -- python -m ubr.main "$@"
