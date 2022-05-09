from pprint import pprint
import argparse
import os, sys
from os.path import join
import logging
from ubr.utils import ensure
from ubr import (
    conf,
    utils,
    s3,
    rds_target,
    mysql_target,
    file_target,
    tgz_target,
    psql_target,
    report,
)
from ubr.descriptions import load_descriptor, find_descriptors, project_name

LOG = logging.getLogger(__name__)

#
# utils
#


KNOWN_TARGET_FNS = [
    file_target,
    tgz_target,
    mysql_target,
    psql_target,
    rds_target,
]
TARGET_MAP = dict(zip(conf.KNOWN_TARGETS, KNOWN_TARGET_FNS))


def module_dispatch(target, func_name, *args, **kwargs):
    """given a target like 'mysql-database' and a function name like 'restore',
    finds the function in the target module and calls with remaining arguments"""
    mod = TARGET_MAP[target]
    ensure(
        hasattr(mod, func_name),
        "module %r (%s) has no function %r" % (mod, target, func_name),
    )
    return getattr(mod, func_name)(*args, **kwargs)


def machinedir(hostname, descriptor_path):
    "returns a path where this machine can deal with this descriptor"
    # ll: /tmp/ubr/civicrm/crm--prod/
    # ll: /tmp/ubr/lax/lax--ci/
    return os.path.join(conf.WORKING_DIR, project_name(descriptor_path), hostname)


def _print_config():
    "debugging, print the configuration the app is running under."
    print("--- command line args")
    _, args = _parseargs(sys.argv[1:])
    pprint(args.__dict__)
    print("--- conf")
    pprint(
        {
            k: v
            for k, v in conf.__dict__.items()
            if not k.startswith("_") and type(v) != type(os)
        }
    )
    print("--- descriptors")
    for descriptor_path in find_descriptors(conf.DESCRIPTOR_DIR):
        print("%r:" % descriptor_path)
        pprint(load_descriptor(descriptor_path, args.paths))


def print_config(fn):
    def wrapper(*args, **kwargs):
        _print_config()
        print("---")
        return fn(*args, **kwargs)

    return wrapper


#
# API
#


def backup_name(target, path):
    """returns the result of `module.backup_name(path)`.
    so, psql_target.backup_name(foo) => foo-psql.tar.gz"""
    return module_dispatch(target, "backup_name", path)


def backup(descriptor, output_dir, opts):
    "consumes a descriptor and creates backups of each of the target's paths"
    return {
        target: module_dispatch(target, "backup", args, output_dir, opts)
        for target, args in descriptor.items()
    }


def restore(descriptor, backup_dir, opts):
    """consumes a descriptor, reading replacements from the given `backup_dir`
    or the most recent datestamped directory"""
    return {
        target: module_dispatch(target, "restore", args, backup_dir, opts)
        for target, args in descriptor.items()
    }


#
#
#


@print_config
def backup_to_rds(hostname, path_list, opts):
    return [
        backup(load_descriptor(path, path_list), None, opts)
        for path in find_descriptors(conf.DESCRIPTOR_DIR)
    ]


def backup_to_file(hostname, path_list, opts):
    results = []
    for descriptor_path in find_descriptors(conf.DESCRIPTOR_DIR):
        descriptor = load_descriptor(descriptor_path, path_list)
        # ll: /tmp/project-name/hostname/somefile.tar.gz
        # ll: /tmp/civicrm/crm--prod/archive-5ea4f412.tar.gz
        backupdir = machinedir(hostname, descriptor_path)
        results.append(backup(descriptor, backupdir, opts))
    return results


def restore_from_file(hostname, path_list, opts):
    "restore backups from local files using descriptors"

    def _do(descriptor_path):
        try:
            restore_dir = machinedir(hostname, descriptor_path)
            return restore(
                load_descriptor(descriptor_path, path_list), restore_dir, opts
            )
        except ValueError as err:
            if not path_list:
                raise  # this is some other ValueError
            # descriptor doesn't have given path. happens with multiple descriptors typically
            LOG.warning("skipping %s: %s" % (descriptor_path, err))

    return list(map(_do, find_descriptors(conf.DESCRIPTOR_DIR)))


def backup_to_s3(hostname, path_list, opts):
    "creates backups using descriptors and then uploads to s3"
    LOG.info("backing up ...")
    results = []
    for descriptor_path in find_descriptors(conf.DESCRIPTOR_DIR):
        project = project_name(descriptor_path)
        backupdir = machinedir(hostname, descriptor_path)
        backup_results = backup(
            load_descriptor(descriptor_path, path_list), backupdir, opts
        )

        # skip upload if the result of the backup didn't return any files.
        if not backup_results:
            continue

        remove_backup_after_upload = True
        results.append(
            s3.upload_backup(
                conf.BUCKET,
                backup_results,
                project,
                utils.hostname(),
                remove_backup_after_upload,
            )
        )
    return results


def download_from_s3(hostname, path_list, opts):
    """by specifying a different hostname, you can download a backup
    from a different machine. Of course you will need that other
    machine's descriptor in /etc/ubr/ ... otherwise it won't know
    what to download and where to restore"""
    LOG.info("restoring ...")
    results = []
    for descriptor_path in find_descriptors(conf.DESCRIPTOR_DIR):
        project = project_name(descriptor_path)
        descriptor = load_descriptor(descriptor_path, path_list)
        download_dir = machinedir(hostname, descriptor_path)
        utils.mkdir_p(download_dir)

        # above path_list narrows descriptor down
        # BUT! if path_list is None, the current descriptor will be read in.
        # this may have different paths to the hostname we want to download from
        # for example: prod--lax.elifesciences.org has 'laxprod'
        #              demo--lax.elifesciences.org has 'laxdemo'
        # and there will be no results for 'laxdemo' (default) when
        # 'prod--lax.elifesciences.org' is specified without paths

        for target, remote_path_list in descriptor.items():
            # explicit paths specified, download exactly what was requested
            if path_list:
                for path in remote_path_list:
                    s3.download_latest_backup(
                        download_dir, conf.BUCKET, project, hostname, target, path
                    )
            else:
                # no paths specified, download all paths for hostname+target
                s3.download_latest_backup(
                    download_dir, conf.BUCKET, project, hostname, target
                )

        results.append((descriptor, download_dir))

    return results


def restore_from_s3(hostname, path_list, opts):
    "same as the download action, but then restores the files/databases/whatever to where they came from"
    # download everything first ...
    results = download_from_s3(hostname, path_list, opts)
    # ll: [({'postgresql-database': ['laxbackfilltest']}, u'/tmp/ubr/lax/prod--lax.elifesciences.org')]
    # ... then restore
    return [
        restore(descriptor, download_dir, opts) for descriptor, download_dir in results
    ]


#
# adhoc
#


def adhoc_s3_download(path_list, opts):
    "connect to s3 and download stuff :)"

    def download(remote_path):
        try:
            # being adhoc, we can't manage a machinename() call
            download_dir = join(conf.WORKING_DIR, os.path.basename(remote_path))
            return s3.download(conf.BUCKET, remote_path, download_dir)
        except AssertionError as err:
            LOG.warning(err)

    return list(map(download, path_list))


def adhoc_file_restore(path_list, opts):
    for source_file, descriptor_str in utils.pairwise(path_list):
        # descriptor_str looks like: 'mysql-database.somedb'
        # exactly like a single entry in a descriptor file
        target, path = descriptor_str.split(".", 1)  # ll: mysql-database, somedb

        # wish this worked, but the source file could have any sort of filename:
        # descriptor = {target: [path]} # ll: {'mysql-database': ['somedb']}
        # restore(descriptor, os.path.dirname(source_file))

        if target == "mysql-database":
            mysql_target.load(path, source_file, dropdb=True)
        elif target == "postgresql-database":
            psql_target.load(path, source_file, dropdb=True)
        else:
            message = "only adhoc *database* restores (mysql and postgresql) are currently handled, not %r"
            LOG.error(message, target)
            raise RuntimeError(message % target)


# checks


def check(hostname, path_list=None):
    "test this host's backup is happening"
    return report.check(hostname, path_list)


def check_all():
    "test *all* hosts backups are happening"
    return report.check_all()


#
# bootstrap
#


def _parseargs(args):
    """basic parsing of args passed in. see `parseargs` for further validation.
    split out so it's result can be used in the `config` action."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--action",
        nargs="?",
        default="backup",
        choices=["config", "check", "check-all", "backup", "restore", "download"],
    )
    parser.add_argument(
        "--location",
        nargs="?",
        default="s3",
        choices=["s3", "file", "rds-snapshot"],
        help="backup/restore files to/from here",
    )
    parser.add_argument(
        "--hostname",
        nargs="?",
        default=utils.hostname(),
        help="used to restore files from another host. default is *this* host (%r)"
        % utils.hostname(),
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=[],
        help="partial backup/restore using specific targets. for example: 'mysql-database.mydb1'",
    )

    # todo: remove once all instances of this are removed
    parser.add_argument("--no-progress-bar", action="store_true")

    return parser, parser.parse_args(args)


def parseargs(args):
    "accepts a list of arguments and returns a list of validated ones"

    parser, args = _parseargs(args)

    if args.action == "download" and args.location == "file":
        parser.error("you can only 'download' when location is 's3'")

    if args.hostname == "adhoc":
        if not args.paths:
            parser.error("all ad-hoc actions *must* supply at least one path")

        if args.action == "restore" and args.location == "file":
            # adhoc file restore
            if len(args.paths) % 2 != 0:
                parser.error(
                    "an even number of paths is required: [source, target, source, target], etc"
                )

    if args.action == "restore" and args.location == "rds-snapshot":
        parser.error("you cannot restore an RDS snapshot using UBR.")

    cmd = [
        getattr(args, key, None) for key in ["action", "location", "hostname", "paths"]
    ]

    opts = {}

    return cmd, opts


@print_config
def config():
    """the CLI action `config`.
    also, a simple demonstration of the `print_config` decorator"""
    pass


def main(args):
    cmd, opts = parseargs(args)
    action, fromloc, hostname, paths = cmd

    if action == "config":
        config()
        exit(0)

    if action == "check":
        exit(len(check(hostname, paths)))

    if action == "check-all":
        exit(len(check_all()))

    if hostname == "adhoc":
        # only a subset of actions available for adhoc locations
        decisions = {
            # ("upload", "s3"): ... # todo: adhoc file uploads to s3 backups bucket would be handy
            ("download", "s3"): adhoc_s3_download,
            ("restore", "file"): adhoc_file_restore,
        }
        return decisions[(action, fromloc)](paths, opts)

    decisions = {
        "backup": {
            "s3": backup_to_s3,
            "file": backup_to_file,
            "rds-snapshot": backup_to_rds,
        },
        "restore": {"s3": restore_from_s3, "file": restore_from_file},
        "download": {"s3": download_from_s3},
    }

    print(
        "action",
        action,
        "fromloc",
        fromloc,
        "hostname",
        hostname,
        "paths",
        paths,
        "opts",
        opts,
    )
    exit(1)

    return decisions[action][fromloc](hostname, paths, opts)


if __name__ == "__main__":
    main(sys.argv[1:])
