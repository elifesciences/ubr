import botocore.errorfactory
from datetime import datetime
import time
import boto3
import logging
from ubr import conf

LOG = logging.getLogger(__name__)


def rds_conn():
    return boto3.client("rds", **conf.AWS)


def rds_snapshot(instance_id, snapshot_name):
    LOG.info("creating RDS snapshot %r from instance: %s", snapshot_name, instance_id)

    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html#RDS.Client.create_db_snapshot
    return rds_conn().create_db_snapshot(
        **{
            "DBSnapshotIdentifier": snapshot_name,
            "DBInstanceIdentifier": instance_id,
            "Tags": [
                {"Key": "author", "Value": "ubr"},
            ],
        }
    )


def wait_until_available(response, max_wait_time_minutes=10):
    """polls `describe_db_snapshots` until the instance described in the given `response` has
    reached the 'available' state or times out."""
    snapshot_id = response["DBSnapshot"]["DBSnapshotIdentifier"]

    start_time = time.time()

    while True:
        elapsed_seconds = int(time.time() - start_time)
        if (elapsed_seconds / 60) > max_wait_time_minutes:
            LOG.error(
                "waited %s minutes, giving up on snapshot: %s",
                max_wait_time_minutes,
                snapshot_id,
            )
            return False

        resp = rds_conn().describe_db_snapshots(DBSnapshotIdentifier=snapshot_id)
        status = resp["DBSnapshots"][0]["Status"]
        if status != "available":
            LOG.info("snapshot %r not available yet: %s", snapshot_id, status)
            time.sleep(10)  # seconds
            continue

        LOG.info("snapshot %r is now %s", snapshot_id, status)

        return True


def snapshot_name(instance_id):
    "returns a unique snapshot name for the given db instance ID"
    # 'automatically' created snapshots (like a daily snapshot) look like:
    #   rds:lax-end2end-2022-04-26-04-50
    # 'manually' created snapshots (like destroying a cloudformation stack) look like:
    #   elife-alfred-prod-snapshot-attacheddb-1s782yrlhghls
    # ubr created snapshots will look like:
    #   ubr-lax-end2end-2022-04-26-04-50

    # "Identifiers must begin with a letter; must contain only ASCII letters, digits, and hyphens; and
    # must not end with a hyphen or contain two consecutive hyphens."

    timestamp = datetime.strftime(datetime.utcnow(), "%Y-%m-%d-%H-%M-%S")
    return "ubr-%s-%s" % (instance_id, timestamp)


def backup(target_list, _, __):
    for instance_id in target_list:
        try:
            wait_until_available(rds_snapshot(instance_id, snapshot_name(instance_id)))
            # wait_until_available(
            #    {
            #        "DBSnapshot": {
            #            "DBSnapshotIdentifier": "ubr-lax-loadtest1-2022-04-26-06-11-31"
            #        }
            #    }
            # )
        except botocore.errorfactory.ClientError as exc:
            if exc.response["Error"]["Code"] == "DBInstanceNotFound":
                LOG.error("RDS instance %r not found, skipping", instance_id)
            else:
                raise exc


def backup_name():
    pass


def restore():
    pass
