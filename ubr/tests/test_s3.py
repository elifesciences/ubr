import os, time, uuid
from os.path import join
from ubr import main, mysql_target, s3, tgz_target, utils, conf
from datetime import datetime
from .base import BaseCase
from moto import mock_s3

@mock_s3
class One(BaseCase):
    def setUp(self):
        self.s3_backup_bucket = "elife-app-backups-test"
        self.project_name = "_" + str(uuid.uuid4())  # underscore means 'test'
        self.hostname = "testmachine"

        # let moto know about the backup bucket ahead of tests
        s3.s3_conn().create_bucket(Bucket=self.s3_backup_bucket)

    def tearDown(self):
        # destroy contents of s3 project bucket
        s3.s3_delete_folder_contents(self.s3_backup_bucket, self.project_name)

    def test_filter_listing(self):
        # this test needs more love!

        input = [
            "civicrm/201507/20150731_ip-10-0-2-118_230108-ELIFECIVICRM-mysql.gz",
            "civicrm/201507/20150731_ip-10-0-2-118_230111-ELIFEDRUPAL-mysql.gz",
            "civicrm/201508/20150731_ip-10-0-2-118_230115-archive.tar.gz",
            "civicrm/201508/20150801_ip-10-0-2-118_230108-ELIFECIVICRM-mysql.gz",
            "civicrm/201508/20150801_ip-10-0-2-118_230112-ELIFEDRUPAL-mysql.gz",
            "civicrm/201508/20150801_ip-10-0-2-118_230115-archive.tar.gz",
        ]

        project = "civicrm"
        host = "ip-10-0-2-118"
        filename = "archive.tar.gz"

        expected_results = [
            "civicrm/201508/20150731_ip-10-0-2-118_230115-archive.tar.gz",
            "civicrm/201508/20150801_ip-10-0-2-118_230115-archive.tar.gz",
        ]

        target = None
        results = s3.filter_listing(input, project, host, target, filename)
        self.assertEqual(results, expected_results)

    def test_foo(self):
        # upload the same two files N times
        # find the latest uploaded of one

        fake_backup_result = {
            "mysql-database": {
                "output": [
                    join(self.fixture_dir, "dummy-db1-mysql.gz"),
                    join(self.fixture_dir, "dummy-db2-mysql.gz"),
                ]
            }
        }

        # upload two lots
        s3.upload_backup(
            self.s3_backup_bucket,
            fake_backup_result,
            self.project_name,
            self.hostname,
            remove=False,
        )
        latest_resp = s3.upload_backup(
            self.s3_backup_bucket,
            fake_backup_result,
            self.project_name,
            self.hostname,
            remove=False,
        )

        # latest_resp ll:
        # ['_d2f9cfe7-3c9b-417b-a535-2b51cc8eba13/201705/20170515_testmachine_165224-dummy-db1-mysql.gz',
        #  '_d2f9cfe7-3c9b-417b-a535-2b51cc8eba13/201705/20170515_testmachine_165227-dummy-db2-mysql.gz']

        # we use the latest resp as our expectation

        names = ["dummy-db1-mysql.gz", "dummy-db2-mysql.gz"]
        latest_resp_idx = dict(list(zip(names, sorted(latest_resp))))

        # latest_resp_idx ll:
        # {'dummy-db1-mysql.gz': '_8f123b46-3314-4de6-9884-ed70709e00e9/201706/20170606_testmachine_170127-dummy-db1-mysql.gz',
        #  'dummy-db2-mysql.gz': '_8f123b46-3314-4de6-9884-ed70709e00e9/201706/20170606_testmachine_170130-dummy-db2-mysql.gz'}

        # ensure that both targets (db1, db2) have the correct file returned
        # when asking for the latest backup
        target = "mysql-database"
        for name in names:
            # 'dummy-db2-mysql.gz', '_d2f9cfe7-3c9b-417b-a535-2b51cc8eba13/201705/20170515_testmachine_165227-dummy-db2-mysql.gz'
            res = s3.latest_backups(
                self.s3_backup_bucket, self.project_name, self.hostname, target, name
            )
            self.assertEqual(len(res), 1)
            returned_name, returned_path = res[
                0
            ]  # the result is a pair of (filename, remote_path_to_filename)

            # we asked for the latest backup for 'db1-mysql.gz', we should be given it back
            self.assertEqual(
                name,
                returned_name,
                "name given %r is not equal to name returned %r"
                % (name, returned_name),
            )

            # the path to 'db1-mysql.gz' should be the same as what was last uploaded
            self.assertEqual(latest_resp_idx[name], returned_path)

        # ensure both targets (db1, db2) are represented when we don't specify a filename
        res = s3.latest_backups(
            self.s3_backup_bucket, self.project_name, self.hostname, target
        )  # no path provided
        self.assertEqual(len(res), 2)
        self.assertEqual(len(dict(res)), 2)

        for fname, remote_path in res:
            self.assertTrue(remote_path.endswith(fname))

@mock_s3
class Upload(BaseCase):
    def setUp(self):
        self.default_opts = conf.DEFAULT_CLI_OPTS
        self.expected_output_dir, self.rmtmpdir = utils.tempdir()
        self.s3_backup_bucket = "elife-app-backups-test"
        self.project_name = "_test"
        self.hostname = "testmachine"

        # let moto know about the backup bucket ahead of tests
        s3.s3_conn().create_bucket(Bucket=self.s3_backup_bucket)

    def tearDown(self):
        self.rmtmpdir()

    def test_backup_is_copied_to_s3(self):
        "the results of a backup are uploaded to s3"
        fixture = os.path.join(self.fixture_dir, "img1.png")
        descriptor = {"tar-gzipped": [fixture, os.path.join(self.fixture_dir, "*/**")]}
        results = main.backup(
            descriptor, output_dir=self.expected_output_dir, opts=self.default_opts
        )

        s3.upload_backup(
            self.s3_backup_bucket, results, self.project_name, self.hostname
        )

        s3obj = s3.s3_file(self.s3_backup_bucket, self.project_name)
        self.assertTrue("Contents" in s3obj)

    def test_multiple_backups_are_copied_to_s3(self):
        mysql_target.create(self.project_name)
        mysql_target.load(
            self.project_name, os.path.join(self.fixture_dir, "mysql_test_table.sql")
        )
        fixture = os.path.join(self.fixture_dir, "img1.png")

        # two things to upload
        descriptor = {"tar-gzipped": [fixture], "mysql-database": [self.project_name]}

        results = main.backup(
            descriptor, output_dir=self.expected_output_dir, opts=self.default_opts
        )
        uploaded_keys = s3.upload_backup(
            self.s3_backup_bucket, results, self.project_name, self.hostname
        )

        # we have the number of keys we expect
        self.assertEqual(2, len(uploaded_keys))

        # the keys we expect exist
        for path in uploaded_keys:
            s3obj = s3.s3_file(self.s3_backup_bucket, path)
            self.assertTrue("Contents" in s3obj)

    def test_backup_is_removed_after_upload(self):
        "after a successful upload to s3, whatever was uploaded is removed"
        fixture = os.path.join(self.fixture_dir, "img1.png")
        descriptor = {"tar-gzipped": [fixture]}
        results = main.backup(
            descriptor, output_dir=self.expected_output_dir, opts=self.default_opts
        )

        s3.upload_backup(
            self.s3_backup_bucket, results, self.project_name, self.hostname
        )

        expected_missing = results["tar-gzipped"]["output"][0]
        self.assertTrue(not os.path.exists(expected_missing))

@mock_s3
class Download(BaseCase):
    def setUp(self):
        self.project_name = "-test"
        self.s3_backup_bucket = "elife-app-backups-test"
        self.hostname = "testmachine"
        self.default_opts = conf.DEFAULT_CLI_OPTS
        self.expected_output_dir, self.rmtmpdir = utils.tempdir()

        # let moto know about the backup bucket ahead of tests
        s3.s3_conn().create_bucket(Bucket=self.s3_backup_bucket)
        s3.s3_delete_folder_contents(self.s3_backup_bucket, self.project_name)

        mysql_target.create("_test")
        mysql_target.load(
            "_test", os.path.join(self.fixture_dir, "mysql_test_table.sql")
        )

    def tearDown(self):
        s3.s3_delete_folder_contents(self.s3_backup_bucket, self.project_name)
        mysql_target.drop("_test")
        self.rmtmpdir()

    def test_download(self):
        "an uploaded file can be downloaded"
        fixture = os.path.join(self.fixture_dir, "img1.png")
        filename = os.path.basename(fixture)
        key = s3.s3_key(self.project_name, self.hostname, fixture)
        s3.upload_to_s3(self.s3_backup_bucket, fixture, key)

        # ensure file exists remotely
        s3obj = s3.s3_file(self.s3_backup_bucket, key)
        self.assertTrue(s3.s3_file_exists(s3obj))

        # download to local
        expected_destination = join(self.expected_output_dir, filename)
        s3.download(self.s3_backup_bucket, key, expected_destination)
        self.assertTrue(os.path.exists(expected_destination))

    def test_download_nonexistant_file(self):
        "a file that doesn't exist on s3 fails sensibly"
        key = s3.s3_key(self.project_name, self.hostname, "fooooooooooooooooooooo.jpg")

        # ensure file DOESNT exist remotely
        s3obj = s3.s3_file(self.s3_backup_bucket, key)
        self.assertFalse(s3.s3_file_exists(s3obj))

        # attempt to download to local
        self.assertRaises(
            AssertionError,
            s3.download,
            self.s3_backup_bucket,
            key,
            self.expected_output_dir,
        )

    def test_find_latest_file(self):
        "a backup can be uploaded to s3 and then detected as the latest and downloaded"
        # create the descriptor
        fixture = os.path.join(self.fixture_dir, "img1.png")
        fixture2 = os.path.join(self.fixture_dir, "*/**")
        paths = [fixture, fixture2]
        descriptor = {"tar-gzipped": paths}

        # backup+upload
        results = main.backup(
            descriptor, output_dir=self.expected_output_dir, opts=self.default_opts
        )
        s3.upload_backup(
            self.s3_backup_bucket, results, self.project_name, self.hostname
        )

        dt = datetime.now()
        ym = dt.strftime("%Y%m")
        ymd = dt.strftime("%Y%m%d")

        for target, path_list in descriptor.items():
            latest = s3.latest_backups(
                self.s3_backup_bucket, self.project_name, self.hostname, target
            )
            self.assertEqual(len(latest), 1)

            filename, latest_path = latest[0]

            expected_filename = tgz_target.filename_for_paths(path_list) + ".tar.gz"
            self.assertEqual(filename, expected_filename)

            expected_prefix = join(
                self.project_name, ym, "%s_%s" % (ymd, self.hostname)
            )
            self.assertTrue(latest_path.startswith(expected_prefix))

    def test_find_latest_mysql(self):
        "a backup can be uploaded to s3 and then detected as the latest and downloaded"
        # do the backup
        descriptor = {"mysql-database": ["_test"]}
        results = main.backup(
            descriptor, output_dir=self.expected_output_dir, opts=self.default_opts
        )
        s3.upload_backup(
            self.s3_backup_bucket, results, self.project_name, self.hostname
        )

        dt = datetime.now()
        ym = dt.strftime("%Y%m")
        ymd = dt.strftime("%Y%m%d")

        for target, path_list in descriptor.items():
            latest = s3.latest_backups(
                self.s3_backup_bucket, self.project_name, self.hostname, target
            )
            self.assertEqual(len(latest), 1)

            filename, latest_path = latest[0]

            expected_filename = "_test-mysql.gz"
            self.assertEqual(filename, expected_filename)

            expected_prefix = join(
                self.project_name, ym, "%s_%s" % (ymd, self.hostname)
            )
            self.assertTrue(latest_path.startswith(expected_prefix))

    def test_find_latest_file_when_multiple_on_same_day(self):
        "many backups can be uploaded to s3 on the same day and only the latest is detected and downloaded"
        fixture = os.path.join(self.fixture_dir, "img1.png")
        descriptor = {"tar-gzipped": [fixture, os.path.join(self.fixture_dir, "*/**")]}

        # do backup1
        results = main.backup(
            descriptor, output_dir=self.expected_output_dir, opts=self.default_opts
        )
        s3.upload_backup(
            self.s3_backup_bucket, results, self.project_name, self.hostname
        )

        # we keep second resolution in the generated file filename.
        # we should be fine but wait a second just in case
        time.sleep(1)

        # do backup2
        results2 = main.backup(
            descriptor, output_dir=self.expected_output_dir, opts=self.default_opts
        )
        s3.upload_backup(
            self.s3_backup_bucket, results2, self.project_name, self.hostname
        )

        # find latest backup
        for target, path_list in descriptor.items():
            # we should know about TWO backups
            known = s3.backups(
                self.s3_backup_bucket, self.project_name, self.hostname, target
            )
            expected_backups = 2
            self.assertEqual(len(known), expected_backups, "We know about %s" % known)

            # and the most recent one should be the last in the list
            expected_latest_path = known[-1]

            latest = s3.latest_backups(
                self.s3_backup_bucket, self.project_name, self.hostname, target
            )
            self.assertEqual(len(latest), 1, "Latest is %s" % latest)

            given_filename, latest_path = latest[0]

            expected_filename = tgz_target.filename_for_paths(path_list) + ".tar.gz"
            self.assertEqual(given_filename, expected_filename)

            self.assertEqual(expected_latest_path, latest_path)

    def test_download_latest(self):
        # create a descriptor
        fixture = os.path.join(self.fixture_dir, "img1.png")
        fixture2 = os.path.join(self.fixture_dir, "img2.jpg")
        paths = [fixture, fixture2]
        descriptor = {"tar-gzipped": paths}

        # backup + upload
        results = main.backup(
            descriptor, output_dir=self.expected_output_dir, opts=self.default_opts
        )
        s3.upload_backup(
            self.s3_backup_bucket, results, self.project_name, self.hostname
        )

        expected_download_dir = join(self.expected_output_dir, "down")
        s3.download_latest_backup(
            expected_download_dir,
            self.s3_backup_bucket,
            self.project_name,
            self.hostname,
            list(descriptor.keys())[0],
        )  # target

        filename = tgz_target.filename_for_paths(paths)
        self.assertTrue(
            os.path.exists(join(expected_download_dir, filename + ".tar.gz"))
        )

        os.system("rm %s" % os.path.abspath(fixture))
        os.system("rm %s" % os.path.abspath(fixture2))
        self.assertFalse(os.path.exists(fixture))
        self.assertFalse(os.path.exists(fixture2))
        results = main.restore(
            descriptor, backup_dir=expected_download_dir, opts=self.default_opts
        )
        self.assertTrue(os.path.exists(fixture))
        self.assertTrue(os.path.exists(fixture2))
