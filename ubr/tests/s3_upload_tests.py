import os, shutil, unittest
from os.path import join
from ubr import main, mysql_target, s3, utils
from datetime import datetime
from unittest import skip

from ubr.tests.basic_tests import BaseCase

skiptest = skip("'cuz")

#
# uploading backup outputs happens after backups, obviously ;)
#

class TestUploadToS3(BaseCase):
    def setUp(self):
        self.expected_output_dir = '/tmp/foo'
        self.s3_backup_bucket = 'elife-app-backups'
        self.project_name = '_test'
        self.hostname = 'testmachine'

    def tearDown(self):
        if os.path.exists(self.expected_output_dir):
            shutil.rmtree(self.expected_output_dir)

    def test_s3_file_exists(self):
        "we can talk to s3 about the existence of files"
        s3obj = s3.s3_file(self.s3_backup_bucket, self.project_name)
        self.assertTrue(isinstance(s3obj, dict))
        self.assertTrue(s3obj.has_key('Contents'))
    def test_backup_is_copied_to_s3(self):
        "the results of a backup are uploaded to s3"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        descriptor = {'tar-gzipped': [fixture, os.path.join(self.fixture_dir, '*/**')]}
        results = main.backup(descriptor, output_dir=self.expected_output_dir)
        
        s3.upload_backup(self.s3_backup_bucket, results, self.project_name, self.hostname)

        s3obj = s3.s3_file(self.s3_backup_bucket, self.project_name)
        self.assertTrue(s3obj.has_key('Contents'))
    def test_multiple_backups_are_copied_to_s3(self):
        mysql_target.create(self.project_name)
        mysql_target.load(self.project_name, os.path.join(self.fixture_dir, 'mysql_test_table.sql'))
        fixture = os.path.join(self.fixture_dir, 'img1.png')

        # two things to upload
        descriptor = {'tar-gzipped': [fixture],
                      'mysql-database': [self.project_name]}

        results = main.backup(descriptor, output_dir=self.expected_output_dir)
        uploaded_keys = s3.upload_backup(self.s3_backup_bucket, results, self.project_name, self.hostname)

        # we have the number of keys we expect
        self.assertEqual(2, len(uploaded_keys))

        # the keys we expect exist
        for path in uploaded_keys:
            s3obj = s3.s3_file(self.s3_backup_bucket, path)
            self.assertTrue(s3obj.has_key('Contents'))
    def test_backup_is_removed_after_upload(self):
        "after a successful upload to s3, whatever was uploaded is removed"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        descriptor = {'tar-gzipped': [fixture]}
        results = main.backup(descriptor, output_dir=self.expected_output_dir)
        
        s3.upload_backup(self.s3_backup_bucket, results, self.project_name, self.hostname)

        expected_missing = results['tar-gzipped']['output'][0]
        self.assertTrue(not os.path.exists(expected_missing))


class TestDownloadFromS3(BaseCase):
    def setUp(self):
        self.project_name = '_test'
        self.s3_backup_bucket = 'elife-app-backups'
        self.hostname = 'testmachine'
        
    def tearDown(self):
        pass

    def test_download(self):
        "an uploaded file can be downloaded"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        filename = os.path.basename(fixture)
        key = s3.s3_key(self.project_name, self.hostname, fixture)
        s3.upload_to_s3(self.s3_backup_bucket, fixture, key)

        # ensure file exists remotely
        s3obj = s3.s3_file(self.s3_backup_bucket, key)
        self.assertTrue(s3.s3_file_exists(s3obj))

        # download to local
        expected_destination = join("/tmp/", filename)
        s3.download_from_s3(self.s3_backup_bucket, key, expected_destination)
        self.assertTrue(os.path.exists(expected_destination))

    def test_download_nonexistant_file(self):
        "a file that doesn't exist on s3 fails sensibly"
        key = s3.s3_key(self.project_name, self.hostname, "fooooooooooooooooooooo.jpg")

        # ensure file DOESNT exist remotely
        s3obj = s3.s3_file(self.s3_backup_bucket, key)
        self.assertFalse(s3.s3_file_exists(s3obj))

        # download to local
        expected_destination = join("/tmp/asdf")
        self.assertRaises(AssertionError, s3.download_from_s3, self.s3_backup_bucket, key, expected_destination)
