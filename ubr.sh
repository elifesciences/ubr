#!/bin/bash
# calls the command line interface to the universal backup/restore script
# assumes script is being run from directory it lives in
# usage: [-h] [--action [{config,check,check-all,backup,restore,download}]] [--location [{s3,file,rds-snapshot}]] [--hostname [HOSTNAME]] [--paths [PATHS [PATHS ...]]] [--no-progress-bar]
set -e

mise run --quiet ubr -- "$@"
