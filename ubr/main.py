"""
usage:

    ubr <configdir> <backup|restore> <dir|s3> [target] [path]

example:
    ./ubr.sh

"""

import os, sys
import yaml
import logging
from ubr import utils, s3, mysql_target, file_target, tgz_target

logging.basicConfig()

logger = logging.getLogger(__name__)
logger.level = logging.INFO

BUCKET = 'elife-app-backups'
CONFIG_DIR = '/etc/ubr/'
RESTORE_DIR = '/tmp/ubr/' # which dir to download files to and restore from

def valid_descriptor(descriptor):
    "return True if the given descriptor is correctly structured."
    assert isinstance(descriptor, dict), "the descriptor must be a dictionary"
    known_targets = targets()['backup'].keys()
    for target_name, target_items in descriptor.items():
        assert isinstance(target_items, list), "a target's list of things to back up must be a list"
        msg = "we don't recognize what a %r is. known targets: %r" % \
          (target_name, ', '.join(known_targets))
        assert target_name in known_targets, msg
    return True

def is_descriptor(path):
    "return True if the given path or filename looks like a descriptor file"
    fname = os.path.basename(path)
    suffix = '-backup.yaml' # descriptors look like: elife-api-backup.yaml or lagotto-backup.yaml
    return fname.endswith(suffix)

def find_descriptors(descriptor_dir):
    "returns a list of descriptors at the given path"
    expandtoabs = lambda path: utils.doall(path, os.path.expanduser, os.path.abspath)
    location_list = map(expandtoabs, utils.list_paths(descriptor_dir))
    return sorted(filter(is_descriptor, filter(os.path.exists, location_list)))

def pname(filename):
    try:
        filename = os.path.basename(filename)
        return filename[:filename.index('-backup.yaml')]
    except ValueError:
        msg = """the given backup descriptor isn't suffixed with '-backup.yaml' -
        I don't know where the project name starts and ends!"""
        logger.warning(msg)
        return None

def load_descriptor(descriptor):
    return yaml.load(open(descriptor, "r"))

def targets():
    return {'backup': {'files': file_target.backup,
                       'tar-gzipped': tgz_target.backup,
                       'mysql-database': mysql_target.backup},

            'restore': {'files': file_target.restore,
                        'tar-gzipped': tgz_target.restore,
                        'mysql-database': mysql_target.restore}}

# looks like: backup('file', ['/tmp/foo', '/tmp/bar'], 'file:///tmp/foo.tar.gz')
def _backup(target, args, destination):
    "a descriptor is a set of targets and inputs to the target functions."
    _targets = targets()
    if _targets['backup'].has_key(target):
        return _targets['backup'][target](args, destination)
    logger.warning("can't handle a %r target. We only know about %r", target, ", ".join(_targets['backup'].keys()))

# looks like: backup({'file': ['/tmp/foo']}, 'file://')
def backup(descriptor, output_dir=None):
    "consumes a descriptor and creates backups of the target's paths"
    if not output_dir:
        output_dir = utils.ymdhms()
    # Python 2.6 compatibility
    backup_targets = {}
    for target, args in descriptor.items():
        backup_targets[target] = _backup(target, args, output_dir)
    return backup_targets

def _restore(target, args, backup_dir):
    try:
        return targets()['restore'][target](args, backup_dir)
    except KeyError:
        pass

def restore(descriptor, backup_dir):
    """consumes a descriptor, reading replacements from the given backup_dir
    or the most recent datestamped directory"""
    restore_targets = {}
    for target, args in descriptor.items():
        restore_targets[target] = _restore(target, args, backup_dir)
    return restore_targets

#
#
#

def file_restore(config_dir=CONFIG_DIR, hostname=utils.hostname()):
    for descriptor in find_descriptors(config_dir):
        restore_dir = os.path.join(RESTORE_DIR, pname(descriptor), hostname)
        return restore(load_descriptor(descriptor), restore_dir)

def s3_backup(config_dir=CONFIG_DIR, hostname=None):
    """hostname is ignored (for now? remote backups in future??)"""
    logger.info("backing up ...")
    for descriptor in find_descriptors(config_dir):
        project = pname(descriptor)
        if not project:
            logger.warning("no project name, skipping given descriptor %r", descriptor)
            continue
        backup_results = backup(load_descriptor(descriptor))
        s3.upload_backup(BUCKET, backup_results, project, utils.hostname())

def s3_restore(config_dir=CONFIG_DIR, hostname=utils.hostname()):
    """
    by specifying a different hostname, you can download a backup
    from a different machine. Of course you will need that other
    machine's descriptor in /etc/ubr/ ... otherwise it won't know
    what to download and where to restore"""
    logger.info("restoring ...")
    for descriptor in find_descriptors(config_dir):
        project = pname(descriptor)
        if not project:
            logger.warning("no project name, skipping given descriptor %r", descriptor)
            continue

        descriptor = load_descriptor(descriptor)

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

def init():
    utils.mkdir_p(RESTORE_DIR)

def main(args):
    init()


    config = args[0]
    action = args[1] if len(args) > 1 else "backup"
    fromloc = args[2] if len(args) > 2 else "s3"
    hostname = args[3] if len(args) > 3 else utils.hostname()
    #target = args[3] if len(args) > 3 else None
    #path_list = args[4] if len(args) > 4 else []

    x = {
        'backup': {
            's3': s3_backup,
            'file': backup,
        },
        'restore': {
            's3': s3_restore,
            'file': file_restore,
        },
    }

    kwargs = {
        'config_dir': config,
        'hostname': hostname,
        #'target': target,
        #'path_list': path_list
    }

    return x[action][fromloc](**kwargs)

if __name__ == '__main__':
    main(sys.argv[1:])
