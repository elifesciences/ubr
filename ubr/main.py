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

TARGETS = {
    'backup': {
        'files': file_target.backup,
        'tar-gzipped': tgz_target.backup,
        'mysql-database': mysql_target.backup},

    'restore': {
        'files': file_target.restore,
        'tar-gzipped': tgz_target.restore,
        'mysql-database': mysql_target.restore}}

def do(action, target, args, destination):
    if action not in TARGETS.keys():
        logger.warn("unknown action %r - I only know how to do %s", action, ", ".join(TARGETS.keys()))
        return None
    if target not in TARGETS[action].keys():
        logger.warn("unknown target %r - I only know about %s", target, ", ".join(TARGETS[action].keys()))
        return None
    return TARGETS[action][target](args, destination)

#
# 'descriptor' wrangling
# what is a 'descriptor'?
# a descriptor is a yaml file in /etc/ubr/ that ends with '-backup.yaml'
# that's it.
#

def pname(path):
    "returns the name of the project given a path to a file"
    try:
        filename = os.path.basename(path)
        return filename[:filename.index('-backup.yaml')]
    except ValueError:
        msg = "given descriptor file isn't suffixed with '-backup.yaml' - I can't determine the project name: %r" % path
        logger.debug(msg)
        return None

def is_descriptor(path):
    "return True if the given path or filename looks like a descriptor file"
    return pname(path) != None

def valid_descriptor(descriptor):
    "return True if the given descriptor is correctly structured."
    assert isinstance(descriptor, dict), "the descriptor must be a dictionary"
    known_targets = TARGETS['backup'].keys()
    for target_name, target_items in descriptor.items():
        assert isinstance(target_items, list), "a target's list of things to back up must be a list"
        msg = "we don't recognize what a %r is. known targets: %s" % \
          (target_name, ', '.join(known_targets))
        assert target_name in known_targets, msg
    return True

def find_descriptors(descriptor_dir):
    "returns a list of descriptors at the given path"
    expandtoabs = lambda path: utils.doall(path, os.path.expanduser, os.path.abspath)
    location_list = map(expandtoabs, utils.list_paths(descriptor_dir))
    return sorted(filter(is_descriptor, filter(os.path.exists, location_list)))

def load_descriptor(descriptor):
    descriptor = yaml.load(open(descriptor, "r"))
    assert valid_descriptor(descriptor), "the given descriptor isn't structured as expected"
    return descriptor

#
#
#

# looks like: backup({'file': ['/tmp/foo']}, 'file://')
def backup(descriptor, output_dir=None):
    "consumes a descriptor and creates backups of each of the target's paths"
    if not output_dir:
        output_dir = utils.ymdhms()
    return {target: do('backup', target, args, output_dir) for target, args in descriptor.items()}

def restore(descriptor, backup_dir):
    """consumes a descriptor, reading replacements from the given backup_dir
    or the most recent datestamped directory"""
    return {target: do('restore', target, args, backup_dir) for target, args in descriptor.items()}

#
#
#

def file_restore(config_dir=CONFIG_DIR, hostname=utils.hostname()):
    "restore backups from local files using descriptors"
    for descriptor in find_descriptors(config_dir):
        restore_dir = os.path.join(RESTORE_DIR, pname(descriptor), hostname)
        return restore(load_descriptor(descriptor), restore_dir)

def s3_backup(config_dir=CONFIG_DIR, hostname=None):
    "create backups using descriptors and then upload to s3"
    # hostname is ignored (for now? remote backups in future??)
    logger.info("backing up ...")
    for descriptor in find_descriptors(config_dir):
        project = pname(descriptor)
        if not project:
            logger.warning("no project name, skipping given descriptor %r", descriptor)
            continue
        backup_results = backup(load_descriptor(descriptor))
        s3.upload_backup(BUCKET, backup_results, project, utils.hostname())

def s3_restore(config_dir=CONFIG_DIR, hostname=utils.hostname()):
    """by specifying a different hostname, you can download a backup
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

def parseargs(args):
    config = args[0]
    action = args[1] if len(args) > 1 else "backup"
    fromloc = args[2] if len(args) > 2 else "s3"
    hostname = args[3] if len(args) > 3 else utils.hostname()
    #target = args[3] if len(args) > 3 else None
    #path_list = args[4] if len(args) > 4 else []
    return config, action, fromloc, hostname

def main(args):
    utils.mkdir_p(RESTORE_DIR)
    config, action, fromloc, hostname = parseargs(args)
    decision_tree = {
        'backup': {
            's3': s3_backup,
            'file': backup,
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
    })

if __name__ == '__main__':
    main(sys.argv[1:])
