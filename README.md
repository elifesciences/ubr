# UBR, Universal Backup/Restore script.

Because I don't want to write another backup script __ever again__.

## requisites

* Python

## usage

    ./ubr.sh <backup|restore|config|check|check-all|download> <dir|s3|rds-snapshot> [target] [path.into.description]

## configuration

All configuration goes in `app.cfg`, see `example.cfg`.

If no `app.cfg` is found `example.cfg` will be used.

Environment variables available are:

* `UBR_CFG_FILE` - use an alternative to `app.cfg`
* `UBR_DESCRIPTION_DIR` - where to look for *descriptor* files (more below)
* `UBR_WORKING_DIR` - root directory for temporary files during a backup (default `/tmp/ubr`)

The final configuration available to UBR can then be viewed with:

    ./ubr.sh --action config

## 'descriptor' files

You write a _descriptor_, a simple YAML file that describes targets and it does
the rest.

For example:

    target:
        - /var/foo/file
        - /etc/bar/file2

A backup target describes the types of paths that are listed under it. For example:

    mysql-database:
        - appdb
        - appdb.users

will target your mysql database and create dumps of the databases `appdb` and
the table `users` in `appdb`. This descriptor:

    tar-gzipped:
        - /var/run/jenkins/config.xml
        - /var/run/jira/whatever.sickof.xml

will create a `.tar.gz` of the files specified.

Each target will have their own rules for dealing with the paths they are given.

A descriptor file can contain multiple targets but you cannot repeat targets.
Only one `tar-gzipped` or `mysql-database` target per descriptor file.

### _tar-gzipped_ and _files_ targets

These two targets are essentially the same, however the `tar-gzipped` target 
simply tars and compresses the results of calling the `files` target.

Everything the `files` target supports is also supported by `tar-gzipped`.

### `files`

Creates a copy of the specified files.

Paths that are directories will be ignored. For example:

    files:
        - /etc/
        
Won't do anything. It won't assume you want all files in that directory. You 
have to specify a file. 

HOWEVER, the `files` target does support globs, so:

    tar-gzipped:
        - /etc/*
        
would tar up and then zip all files in `/etc/` (again, excluding directories).

[Extended globs](https://github.com/miracle2k/python-glob2/) are also supported. 
For example:

    tar-gzipped:
        - /etc/**

would tar up and then zip __everything__ in `/etc/`. All files, all 
sub-directories of files, recursively.


## Copyright & Licence

Copyright 2022 eLife Sciences. Licensed under the [GPLv3](LICENCE.txt)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.



