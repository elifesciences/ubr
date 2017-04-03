import os, tarfile
from ubr import utils, file_target, conf
from conf import logging
import hashlib
from ubr.utils import ensure

LOG = logging.getLogger(__name__)
LOG.level = logging.DEBUG

TMP_SUBDIR = '.tgz-tmp' # this smells

def filename_for_paths(path_list):
    "given a list of filenames, return a predictable string that can be used as a filename"
    return 'archive-' + hashlib.sha1('|'.join(path_list)).hexdigest()[:8]

#
#
#

def integral(archive):
    "return True if gunzip determines the integrity to be ok"
    return 0 == utils.system("gunzip --test %s" % archive)

def unpack(archive):
    msg = "cannot unpack given archive %r - file does not exist!"
    ensure(os.path.exists(archive), msg % archive)

    msg = "will not unpack given archive %r - it doesn't look like an archive"
    ensure(archive.endswith('.gz'), msg % archive)

    msg = "will not unpack given archive %r - gunzip doesn't seem to like it"
    ensure(integral(archive), msg % archive)

    file_listing = tarfile.open(archive, 'r:gz').getnames()
    ensure(0 == utils.system("tar xvzf %s -C /" % archive), "problem extracting archive")

    # not great. check modtime as well?
    return [(f, os.path.isfile(f)) for f in filter(os.path.isfile, file_listing)]

def backup(path_list, destination):
    """does a regular file_backup and then tars and gzips the results.
    the name of the resulting file is 'archive.tar.gz'"""
    destination = os.path.abspath(destination)

    # obfuscate the given destination so it doesn't overwrite anything
    original_destination = destination
    destination = os.path.join(destination, TMP_SUBDIR) # /tmp/foo/.tgz-tmp

    # this will expand any globs (/home/foo/*.jpg), remove any unreadable files, etc
    expanded_path_list = map(os.path.abspath, file_target.wrangle_files(path_list))
    if not expanded_path_list:
        LOG.warn("no files to backup for %r" % path_list)
        return {
            'output': []
        }

    utils.mkdir_p(destination)

    # ll: archive-19928a48
    filename = filename_for_paths(path_list)
    LOG.debug('filename: %s', filename)

    # ll: 2016-01-01-23-59-59/archive-19928a48.tar.gz
    output_path = '%s/%s.tar.gz' % (original_destination, filename)
    LOG.debug("output path: %s", output_path)

    # ok - why the manifest file? turns out there are only so many characters a shell allows,
    # dictated by the kernal. in directories with lots of files, this length is exceeded
    # quickly and returns a mysterious 32517 (or 127 mod 8) return code, which is documented
    # as 'command not found', which *is not* the case at all.
    manifest_path = os.path.join(conf.WORKING_DIR, 'ubr.manifest')
    open(manifest_path, 'w').write("\n".join(expanded_path_list))

    # now when we create the archive file, we tell it to pull the paths from the manifest
    cmd = "cd %(destination)s && tar cvzf %(output_path)s --files-from %(manifest_path)s --absolute-names" % locals()
    ensure(utils.system(cmd) == 0, "failed to create zip")

    return {
        'output': [output_path]
    }

def restore(path_list, backup_dir):
    """assumes a file called 'archive.tar.gz' is in the given directory and that all
    the paths to the files within that tar.gz file are """
    filename = filename_for_paths(path_list)
    archive = os.path.join(backup_dir, filename + ".tar.gz")
    return {
        'output': unpack(archive)
    }
