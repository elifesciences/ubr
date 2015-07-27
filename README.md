# ubr

I don't ever want to write another backup script __ever again__.

They are so damn tedious and every time I write one it's just ever so slightly
different to all the others I've ever written to warrant it's own code.

Screw that noise. This is the one script to rule them all [(and in the darkness 
bind them)](https://www.youtube.com/watch?v=Zp7xHW-JcKk).

## how it works

You write a _descriptor_, a simple YAML file that describes targets and it does
the rest.

For example:

    target:
        - /var/foo/file
        - /etc/bar/file2

A backup target describes the types of paths that are listed under it. For
example:

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

## the _tar-gzipped_ and _files_ targets

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
sub-directories of files, recursively. You often see these double asterisks in 
Git and Mercural `.ignore` files.


## configuration

All configuration comes from sourcing `/etc/ubr/config`

Put your default MYSQL/AWS/whatever config (see `config.example`) in there 
because the system calls I make will just assume (when it can) that it has all 
the permissions it needs as environment variables.

If it doesn't appear as an environment variable, then the application being 
called may try to look for it's config:

    * AWS: http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html
    * BOTO: http://boto.readthedocs.org/en/latest/boto_config_tut.html
    * MySQL: https://dev.mysql.com/doc/refman/5.0/en/environment-variables.html

__Exceptions__ to this rule: 

    * MySQL will be given the value of `MYSQL_USER` rather than `USER`

## command line interface

I have nothing right now, just my desired syntax

    ubr <project> <target> <action>


    how to download a backup?
        - ubr lagotto mysql restore
        
    how to create a backup
        - ubr lagotto mysql backup


## Copyright & Licence

Copyright 2015 eLife Sciences. Licensed under the [GPLv3](LICENCE.txt)

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



