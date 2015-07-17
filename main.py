import os, sys
import yaml

# utils

def first(lst):
    try:
        return lst[0]
    except IndexError:
        return None

def rest(lst):
    return lst[1:]

def doall(val, *args):
    "applies all of the functions given in args to the first val"
    func = first(args)
    if func:
        return doall(func(val), *rest(args))
    return val

def list_paths(d):
    return map(lambda f: os.path.join(d, f), os.listdir(d))

# 

def valid_descriptor(descriptor):
    assert isinstance(descriptor, dict), "the descriptor must be a dictionary"
    known_targets = targets().keys()
    for target_name, target_items in descriptor.items():
        assert isinstance(target_items, list), "a target's list of things to back up must be a list"
        assert target_name in known_targets, "we don't recognize what a %r is. known targets: %r" % (target_name, ', '.join(known_targets))
    return True

def is_descriptor(path):
    "returns true if the given path or filename looks like a backup descriptor"
    fname = os.path.basename(path)
    suffix = '-backup.yaml' # descriptors look like: elife-api-backup.yaml or lagotto-backup.yaml
    return fname.endswith(suffix)

def find_descriptors(descriptor_dir):
    "returns a list of descriptors at the given path"
    location_list = map(lambda path: doall(path, os.path.expanduser, os.path.abspath), list_paths(descriptor_dir))
    return sorted(filter(is_descriptor, filter(os.path.exists, location_list)))

def load_descriptor(descriptor):
    return yaml.load(open(descriptor, "r"))

def file_backup(path_list, destination):
    print 'given paths',path_list,'dest',destination
    errors = filter(lambda p: not os.path.exists(p), path_list)
    if errors:
        print 'the following paths could not be found!'
        print '\n'.join(errors)
    path_list = set(path_list) - set(errors)
    # tar files up
    cmd = 'tar cvzf /tmp/foo.tar.gz %s' % ' '.join(path_list)
    print cmd
    return cmd

def targets():
    return {'file': file_backup}

# looks like: backup('file', ['/tmp/foo', '/tmp/bar'], 'file:///tmp/foo.tar.gz')
def _backup(target, args, destination):
    "a descriptor is a set of targets and inputs to the target functions."
    return targets()[target](args, destination)

def gen_destination(protocol):
    "generates an appropriate destination filename given a destination protocol"
    if protocol == 'file://':
        return '/tmp/foo.tar.gz'

# looks like: backup({'file': ['/tmp/foo']}, 'file://')
def backup(descriptor, destination_protocol='file://'):
    return [_backup(target, args, gen_destination(destination_protocol)) for target, args in descriptor.items()]

#
#
#

def main(args):
    find_descriptors(args)

if __name__ == '__main__':
    main(sys.argv[1:])
