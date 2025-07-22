import pytest
import os
from unittest import mock
from os.path import join
from ubr import main, utils, psql_target as psql, s3, conf
from .base import BaseCase
from moto import mock_aws


@mock_aws
class One(BaseCase):
    def setUp(self):
        self.db1 = "_ubr_testdb"
        psql.create_if_not_exists(self.db1)
        fixture = join(self.fixture_dir, "_ubr_testdb-psql.gz")
        psql.load(self.db1, fixture)

        self.tempdir, self.rmtempdir = utils.tempdir()
        self.s3_backup_bucket = "elife-app-backups-test"
        # let moto know about the backup bucket ahead of tests
        s3.s3_conn().create_bucket(Bucket=self.s3_backup_bucket)

        self.patchers = [
            mock.patch("ubr.utils.hostname", return_value="localhost"),
            mock.patch("ubr.conf.DESCRIPTOR_DIR", self.tempdir),
            mock.patch("ubr.conf.WORKING_DIR", self.tempdir),
            mock.patch("ubr.conf.BUCKET", self.s3_backup_bucket),
        ]
        [p.start() for p in self.patchers]

    def tearDown(self):
        [p.stop() for p in self.patchers]
        self.rmtempdir()

    def test_backup_psql(self):
        # write a descriptor
        # ask to back up to a file
        descriptor = "postgresql-database: [_ubr_testdb]"
        open(join(self.tempdir, "testmachine-backup.yaml"), "w").write(descriptor)
        results = main.main(["--action", "backup", "--location", "file"])
        outputdir = results[0]["postgresql-database"]["output_dir"]
        expected_backup = join(outputdir, psql.backup_name(self.db1))
        self.assertTrue(os.path.exists(expected_backup))

    def test_restore_psql(self):
        # write a descriptor
        # create a backup
        # destroy database
        # restore from backup using same descriptor
        descriptor = "postgresql-database: [_ubr_testdb]"
        open(join(self.tempdir, "testmachine-backup.yaml"), "w").write(descriptor)
        results = main.main(["--action", "backup", "--location", "file"])
        outputdir = results[0]["postgresql-database"]["output_dir"]
        expected_backup = join(outputdir, psql.backup_name(self.db1))
        self.assertTrue(os.path.exists(expected_backup))

        psql.drop(self.db1)
        self.assertFalse(psql.dbexists(self.db1))

        main.main(["--action", "restore", "--location", "file"])
        self.assertTrue(psql.dbexists(self.db1))

    # to/from s3

    def test_backup_psql_to_s3(self):
        # write a descriptor
        # ask to back up to a file
        descriptor = "postgresql-database: [_ubr_testdb]"
        open(join(self.tempdir, "testmachine-backup.yaml"), "w").write(descriptor)
        results = main.main(["--action", "backup", "--location", "s3"])
        # first path of first target
        s3key = s3.s3_file(self.s3_backup_bucket, results[0][0])
        self.assertTrue(s3.s3_file_exists(s3key))


class ParseArgs(BaseCase):
    def setUp(self):
        self.patcher = mock.patch("ubr.utils.hostname", return_value="test-machine")
        self.patcher.start()
        self.default_opts = conf.DEFAULT_CLI_OPTS

    def tearDown(self):
        self.patcher.stop()

    def test_parseargs_minimal_args(self):
        given = ""
        expected = (["backup", "s3", "test-machine", []], self.default_opts)
        self.assertEqual(main.parseargs(given.split()), expected)

    def test_parseargs_two_args(self):
        given = "--action restore"
        expected = (["restore", "s3", "test-machine", []], self.default_opts)
        self.assertEqual(main.parseargs(given.split()), expected)

    def test_parseargs_three_args(self):
        given = "--action restore --location file"
        expected = (["restore", "file", "test-machine", []], self.default_opts)
        self.assertEqual(main.parseargs(given.split()), expected)

    def test_parseargs_four_args(self):
        given = "--action restore --location file --hostname example.org"
        expected = (["restore", "file", "example.org", []], self.default_opts)
        self.assertEqual(main.parseargs(given.split()), expected)

    def test_parseargs_five_args(self):
        "optional fifth+ args to specify targets within the descriptor"
        given = "--action restore --location file --hostname example.org --paths mysql-database.mydb1"
        expected = (
            ["restore", "file", "example.org", ["mysql-database.mydb1"]],
            self.default_opts,
        )
        self.assertEqual(main.parseargs(given.split()), expected)

    def test_parseargs_five_plus_args(self):
        "optional fifth+ args to specify targets within the descriptor"
        given = "--action restore --location file --hostname example.org --paths mysql-database.mydb1 files./opt/thing/ mysql-database.mydb2"
        expected = (
            [
                "restore",
                "file",
                "example.org",
                ["mysql-database.mydb1", "files./opt/thing/", "mysql-database.mydb2"],
            ],
            self.default_opts,
        )
        self.assertEqual(main.parseargs(given.split()), expected)

    def test_download_args(self):
        cases = [
            # download most recent files for this machine from s3
            (
                "--action download",
                (["download", "s3", "test-machine", []], self.default_opts),
            ),
            # same again
            (
                "--action download --location s3",
                (["download", "s3", "test-machine", []], self.default_opts),
            ),
            # download most recent files from the prod machine from s3
            (
                "--action download --location s3 --hostname prod--test-machine",
                (["download", "s3", "prod--test-machine", []], self.default_opts),
            ),
            # download just the mysql database 'thing' from the prod machine from s3
            (
                "--action download --location s3 --hostname prod--test-machine --paths mysql-database.thing",
                (
                    ["download", "s3", "prod--test-machine", ["mysql-database.thing"]],
                    self.default_opts,
                ),
            ),
        ]
        for given, expected in cases:
            actual = main.parseargs(given.split())
            self.assertEqual(
                actual,
                expected,
                "given %r I expected %r but got %r" % (given, expected, actual),
            )

    def test_download_bad_args(self):
        bad_cases = [
            # downloading a file from filesystem?
            (
                "--action download --location file",
                (["download", "file", "test-machine", []], self.default_opts),
            )
        ]
        for given, expected in bad_cases:
            self.assertRaises(SystemExit, main.parseargs, given.split())

    def test_download_adhoc_args(self):
        cases = [
            (
                "--action download --location s3 --hostname adhoc --paths /path/to/uploaded/file.gz",
                (
                    ["download", "s3", "adhoc", ["/path/to/uploaded/file.gz"]],
                    self.default_opts,
                ),
            ),
            (
                "--action download --location s3 --hostname adhoc --paths /a/b/c.gz /a/b/c/d.gz",
                (
                    ["download", "s3", "adhoc", ["/a/b/c.gz", "/a/b/c/d.gz"]],
                    self.default_opts,
                ),
            ),
        ]
        for given, expected in cases:
            actual = main.parseargs(given.split())
            self.assertEqual(
                actual,
                expected,
                "given %r I expected %r but got %r" % (given, expected, actual),
            )

    def test_download_adhoc_bad_args(self):
        cases = [
            # adhoc download without specifying what to download
            "--action download --location s3 --hostname adhoc"
        ]
        for given in cases:
            self.assertRaises(SystemExit, main.parseargs, given.split())


def test_parseargs__restore_rds():
    "an RDS snapshot cannot be restored via UBR"
    given = "--action restore --location rds-snapshot --hostname prod--lax"
    with pytest.raises(SystemExit):
        main.parseargs(given.split())


def test_parseargs__backup_rds():
    "an RDS instance can have a snapshot taken"
    given = "--action backup --location rds-snapshot --hostname prod--lax"
    with mock.patch("ubr.rds_target.backup"):
        main.parseargs(given.split())
