import hashlib
import os, re
import boto3
from os.path import join
from datetime import datetime
from ubr.conf import logging
from ubr import utils, conf
from ubr.utils import ensure

LOG = logging.getLogger(__name__)


def remove_targets(path_list, rooted_at=conf.WORKING_DIR):
    "deletes the list of given paths if the path starts with the given root (default /tmp/)."
    return [
        os.unlink(p)
        for p in filter(os.path.isfile, path_list)
        if p.startswith(rooted_at)
    ]


#
# s3 wrangling
#


def s3_conn():
    return boto3.client("s3", **conf.AWS)


# TODO: cachable
def s3_buckets():
    return [m["Name"] for m in s3_conn().list_buckets()]


def s3_bucket_exists(bname):
    return bname in s3_buckets()


def s3_file(bucket, path):
    "returns the object in the bucket at the given path"
    return s3_conn().list_objects(Bucket=bucket, Prefix=path)


def s3_file_exists(s3obj):
    return "Contents" in s3obj


def s3_key(project, hostname, filename, dt=None):
    if not dt:
        dt = datetime.now()

    ym = dt.strftime("%Y%m")
    ymd = dt.strftime("%Y%m%d")
    hms = dt.strftime("%H%M%S")

    # path, ext = os.path.splitext(filename) # doesn't work for .tar.gz
    fname, ext = os.path.basename(filename), None
    try:
        dotidx = fname.index(".")
        ext = fname[dotidx + 1 :]
        fname = fname[:dotidx]
    except ValueError:
        # couldn't find a dot
        pass
    if ext:
        return (
            "%(project)s/%(ym)s/%(ymd)s_%(hostname)s_%(hms)s-%(fname)s.%(ext)s"
            % locals()
        )
    raise ValueError("given file has no extension.")


def s3_project_files(bucket, project, strip=True):
    "returns a list of backups that exist for the given project"
    # listing = s3_conn().list_objects(Bucket=bucket, Prefix=project)
    paginator = s3_conn().get_paginator("list_objects")
    iterator = paginator.paginate(**{"Bucket": bucket, "Prefix": project})
    results = []
    for page in iterator:
        if strip:
            if "Contents" in page:
                results.extend([i["Key"] for i in page["Contents"]])
    return results


def s3_delete_folder_contents(bucket, path_to_folder):
    ensure(path_to_folder and path_to_folder.strip(), "prefix cannot be empty")
    ensure(
        path_to_folder[0] in ["_", "-", "."],
        "only test dirs can have their contents deleted",
    )
    paths = []
    listing = s3_conn().list_objects(Bucket=bucket, Prefix=path_to_folder)
    if "Contents" in listing:
        paths = [{"Key": item["Key"]} for item in listing["Contents"]]
        s3_conn().delete_objects(Bucket=bucket, Delete={"Objects": paths})
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

TARGET_PATTERNS = {
    "tar-gzipped": r"archive-.+\.tar\.gz",
    "mysql-database": r".+\-mysql\.gz",
    "postgresql-database": r".+\-psql.gz",
}


def filter_listing(file_list, project, host, target=None, filename=""):
    if not filename and target:
        # a specific filename was not given, find all files based on target
        filename = TARGET_PATTERNS[target]
    regex = (
        r"%(project)s/(?P<ym>\d+)/(?P<ymd>\d+)_%(host)s_(?P<hms>\d+)\-%(filename)s"
        % locals()
    )
    cregex = re.compile(regex)
    return list(filter(cregex.match, file_list))


# taken and modified from `tlastowka/calculate_multipart_etag` (GPLv3):
# - https://github.com/tlastowka/calculate_multipart_etag
def generate_s3_etag(source_path):
    "generates an S3-style ETag"
    chunk_size = 8 * 1024 * 1024  # 8 MiB
    md5s = []
    with open(source_path, "rb") as fp:
        while True:
            data = fp.read(chunk_size)
            if not data:
                break
            md5s.append(hashlib.md5(data))

    # precisely $chunk-sized files are still uploaded in multiple parts
    if os.path.getsize(source_path) >= chunk_size:
        digests = b"".join(m.digest() for m in md5s)
        new_md5 = hashlib.md5(digests)
        return '"%s-%s"' % (new_md5.hexdigest(), len(md5s))

    # file smaller than chunk size
    return '"%s"' % md5s[0].hexdigest()


def verify_file(filename, bucket, key):
    "compares the local md5sum with the remote md5sum. files uploaded in multiple parts"
    s3obj = s3_file(bucket, key)
    remote_bytes = int(s3obj["Contents"][0]["Size"])
    local_bytes = os.path.getsize(filename)

    LOG.info("got remote bytes %s for file %s", remote_bytes, key)
    LOG.info("got local bytes %s for file %s", local_bytes, filename)

    if not remote_bytes == local_bytes:
        if remote_bytes > local_bytes:
            raise ValueError(
                "size of REMOTE file (%r) is larger (%r) than local file (%r)"
                % (key, remote_bytes, local_bytes)
            )
        elif local_bytes > remote_bytes:
            raise ValueError(
                "size of LOCAL file (%r) is larger (%r) than remote file (%r)"
                % (key, local_bytes, remote_bytes)
            )

    remote_etag = s3obj["Contents"][0]["ETag"]
    local_etag = generate_s3_etag(filename)

    LOG.info("got remote ETag %r for file %s", remote_etag, key)
    LOG.info("got local ETag %r for file %s", local_etag, filename)

    try:
        if remote_etag != local_etag:
            raise ValueError(
                "ETags for file %r (%s, local) and (%s, remote) do not match"
                % (filename, local_etag, remote_etag)
            )
    except ValueError as e:
        # it's possible the default chunk size has changed from 8192 KiB to ...?
        LOG.error(str(e))

    return True


def upload_to_s3(bucket, src, dest):
    LOG.info("attempting to upload %r to s3://%s/%s", src, bucket, dest)
    s3_conn().upload_file(src, bucket, dest)
    ensure(
        verify_file(src, bucket, dest),
        "local file doesn't match results uploaded to s3 (content md5 or content length difference)",
    )
    return dest


def upload_backup(bucket, backup_results, project, hostname, remove=True):
    """uploads the results of processing a backup.
    `backup_results` should be a dictionary of targets with their results as values.
    each value will have a 'output' key with the outputs for that target.
    these outputs are what is uploaded to s3"""
    upload_targets = [
        target_results["output"]
        for target_results in backup_results.values()
        if target_results
    ]
    upload_targets = list(filter(os.path.exists, utils.flatten(upload_targets)))

    path_list = [
        upload_to_s3(bucket, src, s3_key(project, hostname, src))
        for src in upload_targets
    ]
    # TODO: consider moving this into `main`
    if remove:
        remove_targets(upload_targets, rooted_at=utils.common_prefix(upload_targets))
    return path_list


##


def download(bucket, remote_src, local_dest):
    "remote_src is the s3 key. local_dest is a path to a file on the local filesystem"
    remote_src = remote_src.lstrip("/")
    obj = s3_file(bucket, remote_src)

    msg = "key %r in bucket %r doesn't exist or we have no access to it. cannot download file."
    ensure(s3_file_exists(obj), msg % (remote_src, bucket))

    utils.mkdir_p(os.path.dirname(local_dest))

    s3_conn().download_file(bucket, remote_src, local_dest)
    return local_dest


def backups(bucket, project, hostname, target, path=None):
    "further filtering of the available backups for a given project"
    # TODO: merge this into `s3_project_files` ?
    available_backups = s3_project_files(bucket, project)

    # [u'_e2df12c6-01f4-4ded-a078-a09ad0d4d1e1/201706/20170606_testmachine_171525-dummy-db1-mysql.gz',
    #  u'_e2df12c6-01f4-4ded-a078-a09ad0d4d1e1/201706/20170606_testmachine_171528-dummy-db2-mysql.gz',
    #  u'_e2df12c6-01f4-4ded-a078-a09ad0d4d1e1/201706/20170606_testmachine_171530-dummy-db1-mysql.gz',
    #  u'_e2df12c6-01f4-4ded-a078-a09ad0d4d1e1/201706/20170606_testmachine_171533-dummy-db2-mysql.gz']

    # get a raw list of all of the backups we have
    backups = filter_listing(available_backups, project, hostname, target, path)

    # if path:
    # [u'_8d0ae710-67de-483b-ae9b-3882ed80b656/201706/20170606_testmachine_173226-dummy-db1-mysql.gz',
    #  u'_8d0ae710-67de-483b-ae9b-3882ed80b656/201706/20170606_testmachine_173231-dummy-db1-mysql.gz']

    # if not path:
    # [u'_154a994f-4b06-4121-829f-0c08ffe496ac/201706/20170606_testmachine_173510-dummy-db1-mysql.gz',
    #  u'_154a994f-4b06-4121-829f-0c08ffe496ac/201706/20170606_testmachine_173513-dummy-db2-mysql.gz',
    #  u'_154a994f-4b06-4121-829f-0c08ffe496ac/201706/20170606_testmachine_173515-dummy-db1-mysql.gz',
    #  u'_154a994f-4b06-4121-829f-0c08ffe496ac/201706/20170606_testmachine_173518-dummy-db2-mysql.gz']

    if not backups:
        msg = (
            "no backups found for project %r on host %r (using target %r and path %r)"
            % (project, hostname, target, path)
        )
        LOG.warning(msg)
        return []

    return backups


def latest_backups(bucket, project, hostname, target, backupname=None):
    # there may have been multiple backups
    # figure out the distinct files and return the latest of each
    backup_list = backups(
        bucket, project, hostname, target, backupname
    )  # ll: 'dummy-db1-mysql.gz'
    if not backup_list:
        return []

    if backupname:
        # a specific file was requested so backups at this point should only be specific files:
        # [u'_8d0ae710-67de-483b-ae9b-3882ed80b656/201706/20170606_testmachine_173226-dummy-db1-mysql.gz',
        #  u'_8d0ae710-67de-483b-ae9b-3882ed80b656/201706/20170606_testmachine_173231-dummy-db1-mysql.gz']
        # and we can return the most recent
        return [(backupname, backup_list[-1])]

    # no path was supplied, so we need to find the latest versions of the distinct files uploaded
    # we can't interrogate a descriptor to find out which files unfortunately

    filename_idx = {}
    for s3path in backup_list:
        # split each path into bits and extract the filename (it's the last bit)

        # path: u'-test/201701/20170112_testmachine_164429-archive-2a4c0db0.tar.gz'
        # becomes: [u'-test/201701/20170112', u'testmachine', u'164429-archive-2a4c0db0.tar.gz']
        bits = s3path.split("_", 2)

        # ll: 'archive-2a4c0db0.tar.gz'
        # or: 'dummy-db1-mysql.gz'
        _, s3backupname = bits[-1].split("-", 1)

        path_bucket = filename_idx.get(s3backupname, [])
        path_bucket.append(s3path)
        filename_idx[s3backupname] = path_bucket

    # we should now have something like {'archive.tar.gz': [
    #    'civicrm/201508/20150731_ip-10-0-2-118_230115-archive.tar.gz',
    #    '...']
    # }

    return [(backupnom, sorted(pb)[-1]) for backupnom, pb in filename_idx.items()]


def download_latest_backup(to, bucket, project, hostname, target, path=None):
    if path and "*" in path:
        path = None
    backup_list = latest_backups(bucket, project, hostname, target, path)
    results = []
    for backupname, remote_src in backup_list:
        local_dest = join(to, path or backupname)
        LOG.info("downloading s3 file %r to %r", remote_src, local_dest)
        results.append(download(bucket, remote_src, local_dest))
    return results
