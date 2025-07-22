from ubr import rds_target, utils
from moto import mock_aws
from unittest.mock import patch


@mock_aws
def test_rds_snapshot():
    instance_id = "project-dbname"

    # moto needs to know about this instance first ...
    conn = rds_target.rds_conn()
    conn.create_db_instance(
        DBInstanceIdentifier=instance_id, DBInstanceClass="foo", Engine="postgres"
    )

    # now we can create snapshots
    # snapshot_name = rds_target.snapshot_name(instance_id) # uses timestamps that are tricky to test with
    snapshot_name = "ubr-test-snapshot"
    result = rds_target.rds_snapshot(instance_id, snapshot_name)

    expected = {
        "DBSnapshotIdentifier": snapshot_name,
        "DBInstanceIdentifier": instance_id,
        "Status": "available",
        "DBSnapshotArn": "arn:aws:rds:us-east-1:123456789012:snapshot:" + snapshot_name,
    }

    assert utils.subdict(result["DBSnapshot"], expected.keys()) == expected


@mock_aws
def test_wait_until_available():
    instance_id = "project-dbname"

    # moto needs to know about this instance first ...
    conn = rds_target.rds_conn()
    conn.create_db_instance(
        DBInstanceIdentifier=instance_id, DBInstanceClass="foo", Engine="postgres"
    )

    # now we can create snapshots
    snapshot_name = "ubr-test-snapshot"
    response = rds_target.rds_snapshot(instance_id, snapshot_name)

    assert rds_target.wait_until_available(response, max_wait_time_minutes=1)


@mock_aws
def test_backup():
    instance_id = "project-dbname"
    descriptor = [{"rds_snapshot": [instance_id]}]
    target_list = descriptor[0]["rds_snapshot"]
    output_dir = None
    opts = None

    # moto needs to know about this instance first ...
    conn = rds_target.rds_conn()
    conn.create_db_instance(
        DBInstanceIdentifier=instance_id, DBInstanceClass="foo", Engine="postgres"
    )

    with patch("ubr.rds_target.LOG.info") as mock:
        with patch("ubr.rds_target.snapshot_name", return_value="mocked-snapshot-name"):
            rds_target.backup(target_list, output_dir, opts)
            mock.assert_called_with(
                "snapshot %r is now %s", "mocked-snapshot-name", "available"
            )


@mock_aws
def test_backup__no_db_instance():
    instance_id = "project-dbname"
    descriptor = [{"rds_snapshot": [instance_id]}]
    target_list = descriptor[0]["rds_snapshot"]
    output_dir = None
    opts = None
    with patch("ubr.rds_target.LOG.error") as mock:
        rds_target.backup(target_list, output_dir, opts)
        mock.assert_called_with("RDS instance %r not found, skipping", instance_id)
