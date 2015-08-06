import os, shutil, unittest
from ubr import main, mysql_backup, s3, utils
from datetime import datetime
from unittest import skip
from functools import partial

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

class TestDatabaseRestore(BaseCase):
    def setUp(self):
        self.project_name = '_test'
        self.expected_output_dir = '/tmp/baz/'
        mysql_backup.create(self.project_name)
        mysql_backup.load(self.project_name, os.path.join(self.fixture_dir, 'mysql_test_table.sql'))

    def tearDown(self):
        mysql_backup.drop(self.project_name)

    # NOTE: if tests are being run in parallel, this test modifies a database that
    # another test may be attempting to read from


    def test_restore_modified_db(self):
        "a database can be backed up, the original database altered, the backup restored."
        descriptor = {'mysql-database': [self.project_name]}
        table_test = partial(mysql_backup.fetchone, self.project_name, "select count(*) from table2")
        
        original_expected_result = {u'count(*)': 2}
        self.assertEqual(table_test(), original_expected_result)

        # backup and modify
        main.backup(descriptor, output_dir=self.expected_output_dir)
        mysql_backup.mysql_query(self.project_name, "delete from table2")
        self.assertEqual(table_test(), {u'count(*)': 0})

        # restore the db, run the test
        main.restore(descriptor, backup_dir=self.expected_output_dir)
        self.assertEqual(table_test(), original_expected_result)


    def test_restore_missing_db(self):
        "a database can be backed up, the original database dropped, the backup restored."
        descriptor = {'mysql-database': [self.project_name]}
        table_test = partial(mysql_backup.fetchone, self.project_name, "select count(*) from table2")
        
        original_expected_result = {u'count(*)': 2}
        self.assertEqual(table_test(), original_expected_result)

        # backup and modify
        main.backup(descriptor, output_dir=self.expected_output_dir)
        mysql_backup.drop(self.project_name)
        self.assertFalse(mysql_backup.dbexists(self.project_name))

        # restore the db, run the test
        expected_results = {'mysql-database': {'output': [(self.project_name, True)]}}
        results = main.restore(descriptor, backup_dir=self.expected_output_dir)
        self.assertEqual(results, expected_results)
        
        # check data is as it was prior to dump
        self.assertEqual(table_test(), original_expected_result)
