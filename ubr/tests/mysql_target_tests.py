import os, shutil, unittest
from ubr import main, mysql_backup, s3, utils
from datetime import datetime
from unittest import skip

from ubr.tests.basic_tests import BaseCase

class TestDatabaseBackup(BaseCase):
    def setUp(self):
        self.expected_output_dir = '/tmp/bar'
        self.project_name = '_test'
        mysql_backup.create(self.project_name)
        mysql_backup.load(self.project_name, os.path.join(self.fixture_dir, 'mysql_test_table.sql'))

    def tearDown(self):
        mysql_backup.drop(self.project_name)
        assert self.expected_output_dir.startswith('/tmp'), "cowardly refusing to recursively delete anything outside /tmp ..."
        if os.path.exists(self.expected_output_dir):
            # not all tests create the expected output dir
            shutil.rmtree(self.expected_output_dir)

    def test_dump_db(self):
        "a compressed dump of the test database is created at the expected destination"
        descriptor = {'mysql-database': [self.project_name]}
        results = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(1, len(results['mysql-database']['output']))

        expected_path = os.path.join(self.expected_output_dir, results['mysql-database']['output'][0])
        self.assertTrue(os.path.isfile(expected_path))

    # TODO: not done
    def test_dump_load_query_db(self):
        descriptor = {'mysql-database': [self.project_name]}
        results = main.backup(descriptor, output_dir=self.expected_output_dir)
        expected_path = os.path.join(self.expected_output_dir, results['mysql-database']['output'][0])
        
        self.assertTrue(os.path.isfile(expected_path))

        #mysql_backup.load_gzip(expected_path)        
