import argparse
import os, sys
import logging
from ubr import conf, utils, s3, mysql_target, file_target, tgz_target
from ubr.descriptions import load_descriptor, find_descriptors, pname
from ubr.conf import CONFIG_DIR, RESTORE_DIR, BUCKET

LOG = logging.getLogger(__name__)
_handler = logging.FileHandler('ubr.log')
_handler.setLevel(logging.INFO)
_handler.setFormatter(conf._formatter)
LOG.addHandler(_handler)

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

def file_backup(config_dir=CONFIG_DIR, hostname=utils.hostname(), path_list=None):
    return [backup(load_descriptor(descriptor, path_list)) for descriptor in find_descriptors(config_dir)]

def file_restore(config_dir=CONFIG_DIR, hostname=utils.hostname(), path_list=None):
    "restore backups from local files using descriptors"
    def _do(descriptor):
        restore_dir = os.path.join(RESTORE_DIR, pname(descriptor), hostname)
        return restore(load_descriptor(descriptor, path_list), restore_dir)
    return map(_do, find_descriptors(config_dir))

def s3_backup(config_dir=CONFIG_DIR, hostname=None, path_list=None):
    "create backups using descriptors and then upload to s3"
    # hostname is ignored (for now? remote backups in future??)
    LOG.info("backing up ...")
    for descriptor in find_descriptors(config_dir):
        project = pname(descriptor)
        if not project:
            LOG.warning("no project name, skipping given descriptor %r", descriptor)
            continue
        backup_results = backup(load_descriptor(descriptor, path_list))
        s3.upload_backup(BUCKET, backup_results, project, utils.hostname())

def s3_restore(config_dir=CONFIG_DIR, hostname=utils.hostname(), path_list=None):
    """by specifying a different hostname, you can download a backup
    from a different machine. Of course you will need that other
    machine's descriptor in /etc/ubr/ ... otherwise it won't know
    what to download and where to restore"""
    LOG.info("restoring ...")
    for descriptor in find_descriptors(config_dir):
        project = pname(descriptor)
        if not project:
            LOG.warning("no project name, skipping given descriptor %r", descriptor)
            continue

        descriptor = load_descriptor(descriptor, path_list)

        # ll: /tmp/ubr/civicrm/elife.2020media.net.uk/archive.tar.gz
        download_dir = os.path.join(RESTORE_DIR, project, hostname)
        utils.mkdir_p(download_dir)

        # FIX: ... why do I have to download individually when I can upload all at once?
        for target, path_list in descriptor.items():
            s3.download_latest_backup(download_dir, \
                                      BUCKET, \
                                      project, \
                                      hostname, \
                                      target)

        restore(descriptor, download_dir)

#
# bootstrap
#
        
def parseargs(args):
    "accepts a list of arguments and returns a list of validated ones"
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('config', help='path to a directory where I can find *-backup.yaml files (descriptors)')
        parser.add_argument('action', nargs='?', default='backup', choices=['backup', 'restore'], help='am I backing things up or restoring them?')
        parser.add_argument('location', nargs='?', default='s3', choices=['s3', 'file'], help='am I doing this action from the file system or from S3?')
        parser.add_argument('hostname', nargs='?', default=utils.hostname(), help='if restoring files, should I restore the backup of another host? good for restoring production backups to a different environment')

        # some overlap with the `config` arg: config specifies the set of targets, paths specify which ones.
        parser.add_argument('paths', nargs='*', default=[], help='dot-delimited paths to backup/restore only specific targets. for example: mysql-database.mydb1')

        args = parser.parse_args(args)
        return [getattr(args, key, None) for key in ['config', 'action', 'location', 'hostname', 'paths']]
    except SystemExit:
        LOG.warn("invalid arguments")
        raise

def main(args):
    config, action, fromloc, hostname, paths = parseargs(args)
    decision_tree = {
        'backup': {
            's3': s3_backup,
            'file': file_backup,
        },
        'restore': {
            's3': s3_restore,
            'file': file_restore,
        },
    }
    # x[backup][file](**{'config_dir': ..., 'hostname': 'localhost'})
    return decision_tree[action][fromloc](**{
        'config_dir': config,
        'hostname': hostname,
        'path_list': paths,
    })

if __name__ == '__main__':
    main(sys.argv[1:])
