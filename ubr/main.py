import argparse
import os, sys
from conf import logging
from ubr import conf, utils, s3, mysql_target, file_target, tgz_target
from ubr.descriptions import load_descriptor, find_descriptors, pname
from ubr.conf import RESTORE_DIR, BUCKET

LOG = logging.getLogger(__name__)
_handler = logging.FileHandler('ubr.log')
_handler.setFormatter(conf._formatter)
LOG.addHandler(_handler)
LOG.setLevel(logging.INFO)

TARGETS = {
    'backup': {
        'files': file_target.backup,
        'tar-gzipped': tgz_target.backup,
        'mysql-database': mysql_target.backup
    },

    'restore': {
        'files': file_target.restore,
        'tar-gzipped': tgz_target.restore,
        'mysql-database': mysql_target.restore
    }
}

def do(action, target, args, destination):
    # print 'doing',action,'on',target,'with',args,'at',destination
    if action not in TARGETS.keys():
        LOG.warn("unknown action %r - I only know how to do %s", action, ", ".join(TARGETS.keys()))
        return None
    if target not in TARGETS[action].keys():
        LOG.warn("unknown target %r - I only know about %s", target, ", ".join(TARGETS[action].keys()))
        return None
    return TARGETS[action][target](args, destination)

# looks like: backup({'file': ['/tmp/foo']}, 'file://...')
def backup(descriptor, output_dir=None):
    "consumes a descriptor and creates backups of each of the target's paths"
    return {target: do('backup', target, args, output_dir or utils.ymdhms()) for target, args in descriptor.items()}

def restore(descriptor, backup_dir):
    """consumes a descriptor, reading replacements from the given `backup_dir`
    or the most recent datestamped directory"""
    return {target: do('restore', target, args, backup_dir) for target, args in descriptor.items()}

#
#
#

def file_backup(hostname=utils.hostname(), path_list=None):
    return [backup(load_descriptor(descriptor, path_list)) for descriptor in find_descriptors(conf.CONFIG_DIR)]

def file_restore(hostname=utils.hostname(), path_list=None):
    "restore backups from local files using descriptors"
    def _do(descriptor_path):
        try:
            restore_dir = os.path.join(RESTORE_DIR, pname(descriptor_path), hostname)
            return restore(load_descriptor(descriptor_path, path_list), restore_dir)
        except ValueError as err:
            if not path_list:
                raise # this is some other ValueError
            # descriptor doesn't have given path. happens with multiple descriptors typically
            LOG.warning("skipping %s: %s" % (descriptor_path, err))
    return map(_do, find_descriptors(conf.CONFIG_DIR))

def s3_backup(hostname=None, path_list=None):
    "create backups using descriptors and then upload to s3"
    # hostname is ignored (for now? remote backups in future??)
    LOG.info("backing up ...")
    for descriptor in find_descriptors(conf.CONFIG_DIR):
        project = pname(descriptor)
        if not project:
            LOG.warning("no project name, skipping given descriptor %r", descriptor)
            continue
        backup_results = backup(load_descriptor(descriptor, path_list))
        s3.upload_backup(BUCKET, backup_results, project, utils.hostname())

def s3_download(hostname=utils.hostname(), path_list=None):
    """by specifying a different hostname, you can download a backup
    from a different machine. Of course you will need that other
    machine's descriptor in /etc/ubr/ ... otherwise it won't know
    what to download and where to restore"""
    LOG.info("restoring ...")
    results = []
    for descriptor_path in find_descriptors(conf.CONFIG_DIR):
        project = pname(descriptor_path)
        if not project:
            LOG.warning("no project name, skipping given descriptor %r", descriptor_path)
            continue

        descriptor = load_descriptor(descriptor_path, path_list)

        # ll: /tmp/ubr/civicrm/elife.2020media.net.uk/archive.tar.gz
        download_dir = os.path.join(RESTORE_DIR, project, hostname)
        utils.mkdir_p(download_dir)

        for target, remote_path_list in descriptor.items():
            for path in remote_path_list:
                s3.download_latest_backup(download_dir, *(
                    BUCKET,
                    project,
                    hostname,
                    target,
                    path))

        results.append((descriptor, download_dir))

    return results

def s3_restore(hostname=utils.hostname(), path_list=None):
    "same as the download action, but then restores the files/databases/whatever to where they came from"
    # download everything first ...
    results = s3_download(hostname, path_list)
    # ... then restore
    for descriptor, download_dir in results:
        restore(descriptor, download_dir)

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

    args = parser.parse_args(args)

    if args.action == 'download' and args.location == 'file':
        parser.error("use 's3' for location when downloading")

    return [getattr(args, key, None) for key in ['action', 'location', 'hostname', 'paths']]

def main(args):
    action, fromloc, hostname, paths = parseargs(args)
    decision_tree = {
        'backup': {
            's3': s3_backup,
            'file': file_backup,
        },
        'restore': {
            's3': s3_restore,
            'file': file_restore,
        },
        'download': {
            's3': s3_download,
        }
    }
    # x[backup][file](**{'hostname': 'localhost'})
    return decision_tree[action][fromloc](**{
        'hostname': hostname,
        'path_list': paths,
    })


if __name__ == '__main__':
    main(sys.argv[1:])
