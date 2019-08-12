import argparse
import os, sys
from os.path import join
import logging
from ubr.utils import ensure
from ubr import conf, utils, s3, mysql_target, file_target, tgz_target, psql_target
from ubr.descriptions import load_descriptor, find_descriptors, pname

LOG = logging.getLogger(__name__)

#
# utils
#

def getmod(target):
    target_map = {
        'postgresql-database': psql_target,
        'mysql-database': mysql_target,
        'files': file_target,
        'tar-gzipped': tgz_target,
    }
    ensure(target in target_map, "unknown target %r. known targets: %s" % (target, ", ".join(list(target_map.keys()))))
    return target_map[target]

def dofortarget(target, fnom, *args, **kwargs):
    "given a target like 'mysql-database' and a function name like 'restore', finds the function and calls with remaining args"
    mod = getmod(target)
    ensure(hasattr(mod, fnom), "module %r (%s) has no function %r" % (mod, target, fnom))
    return getattr(mod, fnom)(*args, **kwargs)

def machinedir(hostname, descriptor_path):
    "returns a path where this machine can deal with this descriptor"
    # ll: /tmp/ubr/civicrm/crm--prod/
    # ll: /tmp/ubr/lax/lax--ci/
    return os.path.join(conf.WORKING_DIR, pname(descriptor_path), hostname)

#
#
#

def backup_name(target, path):
    """returns the result of `module.backup_name(path)`.
    so, psql_target.backup_name(foo) => foo-psql.tar.gz"""
    return dofortarget(target, 'backup_name', path)

def backup(descriptor, output_dir, prompt=False):
    "consumes a descriptor and creates backups of each of the target's paths"
    return {target: dofortarget(target, 'backup', args, output_dir, prompt) for target, args in descriptor.items()}

def restore(descriptor, backup_dir, prompt=False):
    """consumes a descriptor, reading replacements from the given `backup_dir`
    or the most recent datestamped directory"""
    return {target: dofortarget(target, 'restore', args, backup_dir, prompt) for target, args in descriptor.items()}

#
#
#

def backup_to_file(hostname, path_list=None, prompt=False):
    results = []
    for descriptor_path in find_descriptors(conf.DESCRIPTOR_DIR):
        descriptor = load_descriptor(descriptor_path, path_list)
        # ll: /tmp/project-name/hostname/somefile.tar.gz
        # ll: /tmp/civicrm/crm--prod/archive-5ea4f412.tar.gz
        backupdir = machinedir(hostname, descriptor_path)
        results.append(backup(descriptor, backupdir, prompt))
    return results

def restore_from_file(hostname, path_list=None, prompt=False):
    "restore backups from local files using descriptors"
    def _do(descriptor_path):
        try:
            restore_dir = machinedir(hostname, descriptor_path)
            return restore(load_descriptor(descriptor_path, path_list), restore_dir, prompt)
        except ValueError as err:
            if not path_list:
                raise # this is some other ValueError
            # descriptor doesn't have given path. happens with multiple descriptors typically
            LOG.warning("skipping %s: %s" % (descriptor_path, err))
    return list(map(_do, find_descriptors(conf.DESCRIPTOR_DIR)))

def backup_to_s3(hostname=None, path_list=None, prompt=False):
    "creates backups using descriptors and then uploads to s3"
    LOG.info("backing up ...")
    results = []
    for descriptor_path in find_descriptors(conf.DESCRIPTOR_DIR):
        project = pname(descriptor_path)
        backupdir = machinedir(hostname, descriptor_path)
        backup_results = backup(load_descriptor(descriptor_path, path_list), backupdir, prompt)
        results.append(s3.upload_backup(conf.BUCKET, backup_results, project, utils.hostname()))
    return results

def download_from_s3(hostname=utils.hostname(), path_list=None, prompt=False):
    """by specifying a different hostname, you can download a backup
    from a different machine. Of course you will need that other
    machine's descriptor in /etc/ubr/ ... otherwise it won't know
    what to download and where to restore"""
    LOG.info("restoring ...")
    results = []
    for descriptor_path in find_descriptors(conf.DESCRIPTOR_DIR):
        project = pname(descriptor_path)
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
                    s3.download_latest_backup(download_dir, *(
                        conf.BUCKET,
                        project,
                        hostname,
                        target,
                        path))
            else:
                # no paths specified, download all paths for hostname+target
                s3.download_latest_backup(download_dir, *(
                    conf.BUCKET,
                    project,
                    hostname,
                    target,
                    None))

        results.append((descriptor, download_dir))

    return results

def restore_from_s3(hostname=utils.hostname(), path_list=None, prompt=False):
    "same as the download action, but then restores the files/databases/whatever to where they came from"
    # download everything first ...
    results = download_from_s3(hostname, path_list)
    # ll: [({'postgresql-database': ['laxbackfilltest']}, u'/tmp/ubr/lax/prod--lax.elifesciences.org')]
    # ... then restore
    return [restore(descriptor, download_dir, prompt) for descriptor, download_dir in results]

#
# adhoc
#

def adhoc_s3_download(path_list, prompt=False):
    "connect to s3 and download stuff :)"
    def download(remote_path):
        try:
            # being adhoc, we can't manage a machinename() call
            download_dir = join(conf.WORKING_DIR, os.path.basename(remote_path))
            return s3.download(conf.BUCKET, remote_path, download_dir)
        except AssertionError as err:
            LOG.warning(err)
    return list(map(download, path_list))

def adhoc_file_restore(path_list, prompt=False):
    for source_file, descriptor_str in utils.pairwise(path_list):
        # descriptor_str looks like: 'mysql-database.somedb'
        # exactly like a single entry in a descriptor file
        target, path = descriptor_str.split('.', 1) # ll: mysql-database, somedb

        # wish this worked, but the source file could have any sort of filename:
        # descriptor = {target: [path]} # ll: {'mysql-database': ['somedb']}
        # restore(descriptor, os.path.dirname(source_file))

        if target == 'mysql-database':
            mysql_target.load(path, source_file, dropdb=True)
        elif target == 'postgresql-database':
            psql_target.load(path, source_file, dropdb=True)
        else:
            message = "only adhoc database restores are currently handled, not `%s`"
            LOG.error(message, target)
            raise RuntimeError(message % target)

#
# bootstrap
#

def parseargs(args):
    "accepts a list of arguments and returns a list of validated ones"
    parser = argparse.ArgumentParser()
    parser.add_argument('action', nargs='?', default='backup', choices=['backup', 'restore', 'download'], help='am I backing things up or restoring them?')
    parser.add_argument('location', nargs='?', default='s3', choices=['s3', 'file'], help='am I doing this action from the file system or from S3?')
    parser.add_argument('hostname', nargs='?', default=utils.hostname(), help='if restoring files, should I restore the backup of another host? good for restoring production backups to a different environment')
    parser.add_argument('paths', nargs='*', default=[], help='dot-delimited paths to backup/restore only specific targets. for example: mysql-database.mydb1')

    # should a prompt be issued when necessary?
    parser.add_argument('--prompt', action='store_true', default=False)

    args = parser.parse_args(args)

    if args.action == 'download' and args.location == 'file':
        parser.error("you can only 'download' when location is 's3'")

    if args.hostname == 'adhoc':
        if not args.paths:
            parser.error("all ad-hoc actions *must* supply at least one path")

        if args.action == 'restore' and args.location == 'file':
            # adhoc file restore
            if len(args.paths) % 2 != 0:
                parser.error("an even number of paths is required: [source, target, source, target], etc")

    return [getattr(args, key, None) for key in ['action', 'location', 'hostname', 'paths', 'prompt']]

def main(args):
    action, fromloc, hostname, paths, prompt = parseargs(args)

    if hostname == 'adhoc':
        decisions = {
            ('download', 's3'): adhoc_s3_download,
            ('restore', 'file'): adhoc_file_restore,
        }
        return decisions[(action, fromloc)](paths, prompt)

    decisions = {
        'backup': {
            's3': backup_to_s3,
            'file': backup_to_file,
        },
        'restore': {
            's3': restore_from_s3,
            'file': restore_from_file,
        },
        'download': {
            's3': download_from_s3,
        }
    }
    return decisions[action][fromloc](hostname, paths, prompt)


if __name__ == '__main__':
    main(sys.argv[1:])
