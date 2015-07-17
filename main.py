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

def targets():
    return {'file': None}

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


#
#
#

def main(args):
    find_descriptors(args)

if __name__ == '__main__':
    main(sys.argv[1:])
