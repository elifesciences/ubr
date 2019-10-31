import re
from datetime import datetime
import logging
from ubr.utils import group_by_many, visit
from ubr import conf, s3
from ubr.descriptions import load_descriptor, find_descriptors, pname

LOG = logging.getLogger(__name__)


def bucket_contents(bucket):
    "returns a list of all keys in the given bucket"
    paginator = s3.s3_conn().get_paginator("list_objects")
    iterator = paginator.paginate(**{"Bucket": bucket, "Prefix": ""})
    results = []
    for page in iterator:
        results.extend([i["Key"] for i in page["Contents"]])
    return results


def parse_prefix_list(prefix_list):
    "splits a bucket prefix-path into a map of data"
    splitter = r"(?P<project>.+)\/(?P<ym>\d+)\/(?P<ymd>\d+)_(?P<host>[a-z0-9\.\-]+)_(?P<hms>\d+)\-(?P<filename>.+)$"
    splitter = re.compile(splitter)
    results = []
    for row in prefix_list:
        try:
            results.append(splitter.match(row).groupdict())
        except AttributeError:
            # failed to parse row. these are in all cases very old or adhoc files and can be safely ignored
            continue
    return results


def filter_backup_list(backup_list):
    "filters the given list of backups, excluding 'hidden' backups, non-production backups and projects/files that are on a blacklist configured in conf.py"
    project_blacklist = conf.REPORT_PROJECT_BLACKLIST
    file_blacklist = conf.REPORT_FILE_BLACKLIST
    # we want to target only working machines and ignore test/retired/etc projects
    def cond(backup):
        return (
            not backup["project"].startswith("_")
            and any([substr in backup["host"] for substr in ["prod", "master-server"]])
            and backup["project"] not in project_blacklist
            and backup["filename"] not in file_blacklist
        )

    return filter(cond, backup_list)


def all_projects_latest_backups_by_host_and_filename(bucket):
    "returns a nested map of the most recent backup for each project+host+filename"
    # this function by itself is really insightful.
    # perhaps have it accept a list of backups rather than creating one itself?
    prefix_list = bucket_contents(bucket)
    backup_list = parse_prefix_list(prefix_list)
    backup_list = filter_backup_list(backup_list)

    # we want a list of the backups for each of the targets
    # {project: {host: {filename: [item-list]}}}
    backup_list = group_by_many(backup_list, ["project", "host", "filename"])

    # we want to transform the deeply nested struct above to retain only the most recent
    # backup. the leaves are sorted lists in ascending order, least to most recent

    def apply_to_backup(x):
        return isinstance(x, list)

    def most_recent_backup(lst):
        return lst[-1]

    # {project: {host: {filename: latest-item}}}
    return visit(backup_list, apply_to_backup, most_recent_backup)


def dtobj_from_backup(backup):
    "given a backup struct, returns a datetime object"
    dtstr = backup["ymd"] + backup["hms"]
    return datetime.strptime(dtstr, "%Y%m%d%H%M%S")


def old_backup(backup):
    "predicate, returns true if given backup is 'old' (older than 2 days)"
    dtobj = dtobj_from_backup(backup)
    diff = datetime.now() - dtobj
    threshold = conf.REPORT_PROBLEM_THRESHOLD
    return diff.days > threshold


#


def print_report(backup_list):
    "given a list of backups, prints it's details"
    result = group_by_many(backup_list, ["project", "host", "filename"])
    for project, hosts in result.items():
        print(project)
        for host, files in hosts.items():
            print(" ", host)
            for filename, backup in files.items():
                backup = backup[0]  # why is this a list ... ?
                ppdt = dtobj_from_backup(backup)
                print("   %s: %s" % (filename, ppdt))


def check_all():
    "check all project that backups are happening"
    results = all_projects_latest_backups_by_host_and_filename(conf.BUCKET)
    problems = []
    for project, hosts in results.items():
        for host, files in hosts.items():
            for filename, backup in files.items():
                old_backup(backup) and problems.append(backup)
                # problems.append(backup)
    if problems:
        print_report(problems)
    return problems


def check(hostname, path_list=None):
    "check self that backups are happening"
    problems = []
    for descriptor_path in find_descriptors(conf.DESCRIPTOR_DIR):
        # 'lax'
        project = pname(descriptor_path)
        # {'postgresql-database': ['lax']}
        descriptor = load_descriptor(descriptor_path, path_list)
        for target, remote_path_list in descriptor.items():
            # [('laxprod-psql.gz', 'lax/201908/20190825_prod--lax.elifesciences.org_230337-laxprod-psql.gz')
            #  ('laxprod-archive.tar.gz', ' 'lax/201908/20190825_prod--lax.elifesciences.org_230337-laxprod-psql.gz')]
            latest_for_target = s3.latest_backups(
                conf.BUCKET, project, hostname, target
            )
            path_list = [s3_path for fname, s3_path in latest_for_target]
            backup_list = parse_prefix_list(path_list)
            for backup in backup_list:
                old_backup(backup) and problems.append(backup)
                # problems.append(backup)
    problems and print_report(problems)
    return problems
