import os, tarfile
from ubr import utils, file_target

import logging

logger = logging.getLogger(__name__)
logger.level = logging.DEBUG

TMP_SUBDIR = '.tgz-tmp'

def integral(archive):
    "return True if gunzip determines the integrity to be ok"
    return 0 == utils.system("gunzip --test %s" % archive)

def unpack(archive):
    msg = "will not unpack given archive %r - it doesn't look like an archive"
    assert archive.endswith('.gz'), msg % archive
    msg = "will not unpack given archive %r - gunzip doesn't seem to like it"
    assert integral(archive), msg % archive

    file_listing = tarfile.open(archive, 'r:gz').getnames()

    assert 0 == utils.system("tar xvzf %s -C /" % archive), "problem extracting archive"
    # not great. check modtime as well?
    return [(f, os.path.isfile(f)) for f in filter(os.path.isfile, file_listing)]

def backup(path_list, destination):
    """does a regular file_backup and then tars and gzips the results.
    the name of the resulting file is 'archive.tar.gz'"""
    destination = os.path.abspath(destination)

    # obfuscate the given destination so it doesn't overwrite anything
    original_destination = destination
    destination = os.path.join(destination, TMP_SUBDIR) # /tmp/foo/.tgz-tmp

    new_path_list = map(os.path.abspath, file_target.wrangle_files(path_list))

    utils.mkdir_p(destination)
    assert new_path_list, "files to backup are empty"

    ctd = destination # change to directory
    #targets = " ".join(new_path_list)
    filename = os.path.basename(original_destination) # this needs to change...!
    filename = 'archive'
    output_path = '%s/%s.tar.gz' % (original_destination, filename)

    # cd 2015-07-27--15-41-36/.tgz-tmp && tar cvzf 2015-07-27--15-41-36/archive.tar.gz *
    # cd /tmp/foo/.tgz-tmp && tar -P -cvzf /tmp/foo/archive.tar.gz *
    #cmd = "cd %(ctd)s && tar cvzf %(output_path)s %(targets)s --absolute-names" % locals()

    # ok - why the manifest file? turns out there is only so many characters a shell allows,
    # dictated by the kernal. in directories with lots of files, this length is exceeded
    # quickly and returns a mysterious 32517 (or 127 mod 8) return code, which is documented
    # as 'command not found', which is not the case at all.
    manifest_path = '/tmp/ubr.manifest'
    #new_path_list.append(manifest_path) # we don't want this file restored
    open(manifest_path, 'w').write("\n".join(new_path_list))

    cmd = "cd %(ctd)s && tar cvzf %(output_path)s --files-from %(manifest_path)s --absolute-names" % locals()
    logger.info("running command %r", cmd)
    assert utils.system(cmd) == 0, "failed to create zip"

    return {
        'output': [output_path]
    }

def restore(path_list, backup_dir):
    "assumes a file called 'archive.tar.gz' is in the given directory and that all the paths to the files within that tar.gz file are "
    archive = os.path.join(backup_dir, "archive.tar.gz")
    return {
        'output': unpack(archive)
    }
