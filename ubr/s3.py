import os, sys
from os.path import join
from datetime import datetime
import threading
from conf import logging
from ubr import utils

LOG = logging.getLogger(__name__)

def remove_targets(path_list, rooted_at="/tmp/"):
    "deletes the list of given paths if the path starts with the given root (default /tmp/)."
    return map(os.unlink, filter(lambda p: p.startswith(rooted_at), filter(os.path.isfile, path_list)))


#
# s3 wrangling
#

def s3_conn():
    import boto3
    return boto3.client("s3")

# TODO: cachable
def s3_buckets():
    return [m['Name'] for m in s3_conn().list_buckets()]

def s3_bucket_exists(bname):
    return bname in s3_buckets()

def s3_file(bucket, path):
    "returns the object in the bucket at the given path"
    return s3_conn().list_objects(Bucket=bucket, Prefix=path)

def s3_file_exists(s3obj):
    return s3obj.has_key('Contents')

def s3_key(project, hostname, filename, dt=None):
    if not dt:
        dt = datetime.now()

    ym = dt.strftime("%Y%m")
    ymd = dt.strftime("%Y%m%d")
    hms = dt.strftime("%H%M%S")

    # path, ext = os.path.splitext(filename) # doesn't work for .tar.gz
    fname, ext = os.path.basename(filename), None
    try:
        dotidx = fname.index('.')
        ext = fname[dotidx + 1:]
        fname = fname[:dotidx]
    except ValueError:
        # couldn't find a dot
        pass
    if ext:
        return "%(project)s/%(ym)s/%(ymd)s_%(hostname)s_%(hms)s-%(fname)s.%(ext)s" % locals()
    raise ValueError("given file has no extension.")

def s3_project_files(bucket, project, strip=True):
    "returns a list of backups that exist for the given project"
    listing = s3_conn().list_objects(Bucket=bucket, Prefix=project)
    if strip:
        if listing.has_key('Contents'):
            return map(lambda i: i['Key'], listing['Contents'])
        return [] # nothing exists!
    return listing

def s3_delete_folder_contents(bucket, path_to_folder):
    assert path_to_folder and path_to_folder.strip(), "prefix cannot be empty"
    assert path_to_folder[0] in ["_", "-", "."], "only test dirs can have their contents deleted"
    paths = []
    listing = s3_conn().list_objects(Bucket=bucket, Prefix=path_to_folder)
    if listing.has_key('Contents'):
        paths = [{'Key': item['Key']} for item in listing['Contents']]
        s3_conn().delete_objects(Bucket=bucket, Delete={'Objects': paths})
    return paths

"""
# totally works but is too difficult to work with
# going with the filtering-on-filename approach
def parse_path_list(path_list):
    def grouper(item):
        bits = item.split('/', 1)
        if len(bits) == 1:
            # try splitting by underscore
            return item.split('_', 1)
        return bits
    return utils.group(path_list, grouper)

def parse_s3_project_files(bucket, project):
    "returns a nested OrderedDict instance that lets you traverse backups using the naming scheme in `s3_key`"
    return parse_path_list(s3_project_files(bucket, project))[project]
"""

def filterasf(file_list, project, host, filename):
    import re
    regex = r"%(project)s/(?P<ym>\d+)/(?P<ymd>\d+)_%(host)s_(?P<hms>\d+)\-%(filename)s" % locals()
    cregex = re.compile(regex)
    return filter(cregex.match, file_list)


class ProgressPercentage(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename)) if not filename.startswith("s3://") else 0.0
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self.done = False

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            self.done = percentage == 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)        " % \
                (self._filename, self._seen_so_far,
                 self._size, percentage))
            sys.stdout.flush()

class DownloadProgressPercentage(ProgressPercentage):
    def __init__(self, remote_filename):
        super(DownloadProgressPercentage, self).__init__(remote_filename)
        assert remote_filename.startswith('s3://'), "given filename doesn't look like s3://bucket/some/path"
        bits = filter(None, remote_filename.split('/'))
        bucket, path = bits[1], "/".join(bits[2:])
        self._size = int(s3_file(bucket, path)['Contents'][0]['Size'])

def verify_file(filename, bucket, key):
    """{u'MaxKeys': 1000, u'Prefix': '_test/201507/20150729_113709_testmachine-archive.tar.gz', u'Name': 'elife-app-backups', 'ResponseMetadata': {'HTTPStatusCode': 200, 'HostId': 'ux+6JS8Snw+wKj7wuUpMF3ajq11aVYLjcFNpYhKpv7WOOTAXcZoMo4Nmpf0GdYQKFYrT60nKCwM=', 'RequestId': 'EBC29E161C7FEAF1'}, u'Marker': '', u'IsTruncated': False, u'Contents': [{u'LastModified': datetime.datetime(2015, 7, 29, 10, 37, 11, tzinfo=tzutc()), u'ETag': '"4c5a880597d564134192e812336c3d9e"', u'StorageClass': 'STANDARD', u'Key': '_test/201507/20150729_113709_testmachine-archive.tar.gz', u'Owner': {u'DisplayName': 'aws', u'ID': '8a202ef63dada93bea1dc89ddcbc0772245e0f9e8d2d818f8c3c66e193065766'}, u'Size': 234278}]}

    http://docs.aws.amazon.com/AWSAndroidSDK/latest/javadoc/com/amazonaws/services/s3/model/ObjectMetadata.html#getETag()
    """
    s3obj = s3_file(bucket, key)
    remote_bytes = int(s3obj['Contents'][0]['Size'])
    local_bytes = os.path.getsize(filename)

    LOG.info("got remote bytes %s for file %s", remote_bytes, key)
    LOG.info("got local bytes %s for file %s", local_bytes, filename)

    if not remote_bytes == local_bytes:
        if remote_bytes > local_bytes:
            raise ValueError("size of REMOTE file (%r) is larger (%r) than local file (%r)" % (key, remote_bytes, local_bytes))
        elif local_bytes > remote_bytes:
            raise ValueError("size of LOCAL file (%r) is larger (%r) than remote file (%r)" % (key, local_bytes, remote_bytes))

    remote_md5 = s3obj['Contents'][0]['ETag']
    remote_md5 = remote_md5.strip('"') # yes, really. fml.
    local_md5 = utils.generate_file_md5(filename)

    LOG.info("got remote md5 %s for file %s", remote_md5, key)
    LOG.info("got local md5 %s for file %s", local_md5, filename)

    try:
        if remote_md5 != local_md5:
            raise ValueError("MD5 sums for file (%r) local (%r) and remote (%r) do not match" % (filename, local_bytes, remote_bytes))
    except ValueError, e:
        # this happens when S3 does a multipart upload on large files apparently.
        # we're using the convenience function `upload_file` and `download_file`
        # that automatically chooses what method is needed. log the error, but
        # as long as the bytes are identical, I don't mind.
        LOG.error(e.message)

    return True

def upload_to_s3(bucket, src, dest):
    LOG.info("attempting to upload %r to s3://%s/%s", src, bucket, dest)
    inst = ProgressPercentage(src)
    s3_conn().upload_file(src, bucket, dest, Callback=inst)
    assert inst.done, "failed to complete uploading to s3"
    assert verify_file(src, bucket, dest), "local file doesn't match results uploaded to s3 (content md5 or content length difference)"
    return dest

def upload_backup(bucket, backup_results, project, hostname):
    """uploads the results of processing a backup.
    `backup_results` should be a dictionary of targets with their results as values.
    each value will have a 'output' key with the outputs for that target.
    these outputs are what is uploaded to s3"""
    upload_targets = [target_results['output'] for target_results in backup_results.values()]
    upload_targets = filter(os.path.exists, utils.flatten(upload_targets))
    path_list = [upload_to_s3(bucket, src, s3_key(project, hostname, src)) for src in upload_targets]
    remove_targets(upload_targets, rooted_at=utils.common_prefix(upload_targets))
    return path_list

##

def download_from_s3(bucket, remote_src, local_dest):
    "remote_src is the s3 key. local_dest is a path to a file on the local filesystem"
    remote_src = remote_src.lstrip('/')
    obj = s3_file(bucket, remote_src)

    msg = "key %r in bucket %r doesn't exist or we have no access to it. cannot download file."
    assert s3_file_exists(obj), msg % (remote_src, bucket)

    inst = DownloadProgressPercentage("s3://%(bucket)s/%(remote_src)s" % locals())
    utils.mkdir_p(os.path.dirname(local_dest))
    s3_conn().download_file(bucket, remote_src, local_dest, Callback=inst)


def backups(bucket, project, hostname, target, path=None):
    "further filtering of the available backups for a given project"
    # TODO: merge this into `s3_project_files` ?
    available_backups = s3_project_files(bucket, project)

    # FIXME: this sort of logic shouldn't live here.
    # FUTURELUKE: uh huh. where then, past-Luke?
    lu = {
        'tar-gzipped': 'archive-.+.tar.gz',
        'mysql-database': '.+-mysql.gz',
    }
    filename = lu[target]
    if path and target == 'mysql':
        filename = path + '-mysql.gz'
    # /FIXME

    # get a raw list of all of the backups we have
    backups = filterasf(available_backups, project, hostname, filename)
    if not backups:
        msg = "no backups found for project %r on host %r (using target %r and path %r)"
        LOG.warning(msg, project, hostname, target, path)
        return []

    # we have potentially many files at this point
    # we only want to download the latest ones

    if path:
        # a specific file is wanted, easy
        backups = [backups[-1]]

    # get the date of the last upload and filter everything else out
    most_recent = backups[-1]
    prefix = most_recent[:most_recent.index('_')]
    return filter(lambda p: p.startswith(prefix), backups)

def latest_backups(bucket, project, hostname, target, path=None):
    # there may have been multiple backups
    # figure out the distinct files and return the latest of each
    backup_list = backups(bucket, project, hostname, target, path)
    print 'got backups',backup_list
    mmap = {}
    for path in backup_list:
        # path ll: u'-test/201701/20170112_testmachine_164429-archive-2a4c0db0.tar.gz'
        
        # ll: [u'-test/201701/20170112', u'testmachine', u'164429-archive-2a4c0db0.tar.gz']
        key = path.split('_', 2)

        # ll: u'archive-2a4c0db0.tar.gz'
        key = key[2].split('-', 1)[1]

        if not mmap.has_key(key):
            mmap[key] = []
        mmap[key].append(path)

    # we should now have something like {'archive.tar.gz': [
    #    'civicrm/201508/20150731_ip-10-0-2-118_230115-archive.tar.gz',
    #    '...']
    # }

    return [(backuptype, sorted(filelist)[-1]) for backuptype, filelist in mmap.items()]

def download_latest_backup(to, bucket, project, hostname, target, path=None):
    backup_list = latest_backups(bucket, project, hostname, target, path)
    x = []
    for backuptype, remote_src in backup_list:
        local_dest = join(to, backuptype)
        LOG.info("downloading s3 file %r to %r", remote_src, local_dest)
        x.append(download_from_s3(bucket, remote_src, join(to, backuptype)))
    return x
