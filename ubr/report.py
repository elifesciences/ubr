import re
import json
import humanize as humanise
from datetime import datetime, timedelta
import os
import logging
from ubr.utils import group_by_many, visit
from ubr import conf, s3
from ubr.descriptions import load_descriptor, pname

LOG = logging.getLogger(__name__)


def check(hostname, path_list=None):
    "checks that self-test backups are happening"
    now = datetime.today() + timedelta(days=4)
    problems = []
    threshold = 2  # days
    print(hostname)
    # for descriptor_path in find_descriptors(conf.DESCRIPTOR_DIR):
    for descriptor_path in ["lax-backup.yaml"]:
        project = pname(descriptor_path)  # lax
        descriptor = load_descriptor(
            descriptor_path, path_list
        )  # {'postgresql-database': ['lax']}
        for target, remote_path_list in descriptor.items():
            latest_for_target = s3.latest_backups(
                conf.BUCKET, project, hostname, target
            )
            for fname, s3_path in latest_for_target:
                # (-> path (split '/') last (split '_') first))
                # lax/201908/20190818_prod--lax.elifesciences.org_230323-laxprod-psql.gz => 20190818
                datebit = s3_path.split("/")[-1].split("_")[0]
                dtobj = datetime.strptime(datebit, "%Y%m%d")
                diff = now - dtobj
                print("* " + fname + ": " + humanise.naturaltime(diff))
                if diff.days > threshold:
                    problems.append(
                        {
                            hostname: {
                                fname: s3_path,
                                "age": dtobj.isoformat(),
                                "age-in-days": diff.days,
                            }
                        }
                    )
            print
    if problems:
        print("problems")
        print(json.dumps(problems, indent=4))
    return problems


#


def extract_hostnames(path_list):
    results = []
    for path in path_list:
        try:
            results.append(path.split("_")[1])
        except Exception as e:
            print("failed to parse file %r, skipping: %s" % (str(e), path))
    return set(results)


def bucket_contents(bucket):
    "returns a list of all keys in the given bucket"
    fname = "/tmp/ubr-s3-cached.json"
    if os.path.exists(fname):
        return json.load(open(fname, "r"))

    paginator = s3.s3_conn().get_paginator("list_objects")
    iterator = paginator.paginate(**{"Bucket": bucket, "Prefix": ""})
    results = []
    for page in iterator:
        results.extend([i["Key"] for i in page["Contents"]])

    json.dump(results, open(fname, "w"), indent=4)

    return results


def parse_contents(prefix_list):
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


def print_report(backup_list):
    "given a list of backups, prints it's details"
    result = group_by_many(backup_list, ["project", "host", "filename"])
    for project, hosts in result.items():
        print(project)
        for host, files in hosts.items():
            print(" ", host)
            for filename, backup in files.items():
                print("   ", filename, ": ", backup[0]["ymd"])  # why is this a list? ..


def all_projects_latest_backups_by_host_and_filename(bucket):
    prefix_list = bucket_contents(bucket)
    parsed_prefix_list = parse_contents(prefix_list)

    # TODO: stick in conf
    project_blacklist = ["civicrm"]
    file_blacklist = [
        "archive-d162efcb.tar.gz",  # elife-metrics, old-style backup
        "archive-b40e0f85.tar.gz",  # journal-cms, old-style backup
        "elifedashboardprod-psql.gz",  # elife-dashboard, old-style backup
    ]
    # we want to target only working machines and ignore test/retired/etc projects
    def cond(backup):
        return (
            not backup["project"].startswith("_")
            and any([substr in backup["host"] for substr in ["prod", "master-server"]])
            and backup["project"] not in project_blacklist
            and backup["filename"] not in file_blacklist
        )

    result = filter(cond, parsed_prefix_list)

    # we want a list of the backups for each of the targets
    # {project: {host: {filename: [item-list]}}}
    result = group_by_many(result, ["project", "host", "filename"])

    # we want to transform the deeply nested struct above to retain only the most recent
    # backup. the leaves are sorted lists in ascending order, least to most recent

    def apply_to_backup(x):
        return isinstance(x, list)

    def most_recent_backup(lst):
        return lst[-1]

    # {project: {host: {filename: latest-item}}}
    return visit(result, apply_to_backup, most_recent_backup)


def old_backup(backup):
    dtobj = datetime.strptime(backup["ymd"], "%Y%m%d")
    diff = datetime.now() - dtobj
    threshold = 2  # days
    return diff.days > threshold


def check_all():
    results = all_projects_latest_backups_by_host_and_filename(conf.BUCKET)
    problems = []
    for project, hosts in results.items():
        for host, files in hosts.items():
            for filename, backup in files.items():
                old_backup(backup) and problems.append(backup)
                # problems.append(backup)
    problems and print_report(problems)
    return problems
