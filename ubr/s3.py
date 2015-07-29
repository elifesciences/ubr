import os, sys
from datetime import datetime
import threading
import logging
from ubr import utils

logger = logging.getLogger(__name__)

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

def s3_key(project, hostname, filename):
    now = datetime.now()
    ym = now.strftime("%Y%m")
    ymdhms = now.strftime("%Y%m%d_%H%M%S")
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
        return "%(project)s/%(ym)s/%(ymdhms)s_%(hostname)s-%(fname)s.%(ext)s" % locals()
    raise ValueError("given file has no extension.")

class ProgressPercentage(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
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
                "\r%s  %s / %s  (%.2f%%)" % (self._filename, self._seen_so_far,
                                             self._size, percentage))
            sys.stdout.flush()

def generate_file_md5(filename, blocksize=2**20):
    "http://stackoverflow.com/questions/1131220/get-md5-hash-of-big-files-in-python"
    import hashlib
    m = hashlib.md5()
    with open(filename, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()

def verify_file(filename, bucket, key):
    """{u'MaxKeys': 1000, u'Prefix': '_test/201507/20150729_113709_testmachine-archive.tar.gz', u'Name': 'elife-app-backups', 'ResponseMetadata': {'HTTPStatusCode': 200, 'HostId': 'ux+6JS8Snw+wKj7wuUpMF3ajq11aVYLjcFNpYhKpv7WOOTAXcZoMo4Nmpf0GdYQKFYrT60nKCwM=', 'RequestId': 'EBC29E161C7FEAF1'}, u'Marker': '', u'IsTruncated': False, u'Contents': [{u'LastModified': datetime.datetime(2015, 7, 29, 10, 37, 11, tzinfo=tzutc()), u'ETag': '"4c5a880597d564134192e812336c3d9e"', u'StorageClass': 'STANDARD', u'Key': '_test/201507/20150729_113709_testmachine-archive.tar.gz', u'Owner': {u'DisplayName': 'aws', u'ID': '8a202ef63dada93bea1dc89ddcbc0772245e0f9e8d2d818f8c3c66e193065766'}, u'Size': 234278}]}

    http://docs.aws.amazon.com/AWSAndroidSDK/latest/javadoc/com/amazonaws/services/s3/model/ObjectMetadata.html#getETag()
    """
    s3obj = s3_file(bucket, key)
    remote_bytes = int(s3obj['Contents'][0]['Size'])
    local_bytes = os.path.getsize(filename)

    logger.info("got remote bytes %s for file %s", remote_bytes, key)
    logger.info("got local bytes %s for file %s", local_bytes, filename)
    
    if not remote_bytes == local_bytes:
        if remote_bytes > local_bytes:
            raise ValueError("size of REMOTE file is larger than local file")
        elif local_bytes > remote_bytes:
            raise ValueError("size of LOCAL file is larger than remote file")

    remote_md5 = s3obj['Contents'][0]['ETag']
    remote_md5 = remote_md5.strip('"') # yes, really. fml.
    local_md5 = generate_file_md5(filename)

    logger.info("got remote md5 %s for file %s", remote_md5, key)
    logger.info("got local md5 %s for file %s", local_md5, filename)

    if remote_md5 != local_md5:
        raise ValueError("local and remote md5 sums do not match")
    
    return True
    

def upload_to_s3(bucket, src, dest):
    logger.info("attempting to upload %r to s3://%s/%s", src, bucket, dest)
    inst = ProgressPercentage(src)
    s3_conn().upload_file(src, bucket, dest, Callback=inst)
    if not inst.done:
        raise ValueError("failed to complete uploading to s3")
    if not verify_file(src, bucket, dest):
        raise ValueError("local file doesn't match that one uploaded to s3 (content md5 or content length difference)")
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
