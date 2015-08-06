import os, sys, shutil
import yaml
import logging
from ubr import utils, s3, mysql_target, file_target, tgz_target

logging.basicConfig()

logger = logging.getLogger(__name__)
logger.level = logging.INFO

#logger.addHandler(logging.StreamHandler())

def valid_descriptor(descriptor):
    assert isinstance(descriptor, dict), "the descriptor must be a dictionary"
    known_targets = targets()['backup'].keys()
    for target_name, target_items in descriptor.items():
        assert isinstance(target_items, list), "a target's list of things to back up must be a list"
        msg = "we don't recognize what a %r is. known targets: %r" % \
          (target_name, ', '.join(known_targets))
        assert target_name in known_targets, msg
    return True

def is_descriptor(path):
    "returns true if the given path or filename looks like a backup descriptor"
    fname = os.path.basename(path)
    suffix = '-backup.yaml' # descriptors look like: elife-api-backup.yaml or lagotto-backup.yaml
    return fname.endswith(suffix)

def find_descriptors(descriptor_dir):
    "returns a list of descriptors at the given path"
    expandtoabs = lambda path: utils.doall(path, os.path.expanduser, os.path.abspath)
    location_list = map(expandtoabs, utils.list_paths(descriptor_dir))
    return sorted(filter(is_descriptor, filter(os.path.exists, location_list)))

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
    try:
        return targets()['backup'][target](args, destination)
    except KeyError:
        pass

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

def s3_backup():
    pass

def s3_restore():
    pass

#
# bootstrap
#

def main(args):

    def pname(filename):
        try:
            filename = os.path.basename(filename)
            return filename[:filename.index('-backup.yaml')]
        except ValueError:
            msg = """the given backup descriptor isn't suffixed with '-backup.yaml' -
            I don't know where the project name starts and ends!"""
            logger.warning(msg)
            return None

    given_dir = args[0]
    bucket = 'elife-app-backups'
    for descriptor in find_descriptors(given_dir):
        project = pname(descriptor)
        if not project:
            logger.warning("no project name, skipping given descriptor %r", descriptor)
            continue
        s3.upload_backup(bucket, backup(load_descriptor(descriptor)), project, utils.hostname())

if __name__ == '__main__':
    main(sys.argv[1:])
