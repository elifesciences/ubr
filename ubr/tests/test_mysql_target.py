import os
from ubr import main, mysql_target, conf, utils
from functools import partial
from .base import BaseCase

class TestDatabaseBackup(BaseCase):
    def setUp(self):
        self.expected_output_dir, self.rmtmpdir = utils.tempdir()
        self.project_name = '_test'
        mysql_target.create(self.project_name)
        mysql_target.load(self.project_name, os.path.join(self.fixture_dir, 'mysql_test_table.sql'))

    def tearDown(self):
        self.rmtmpdir()
        mysql_target.drop(self.project_name)

    def test_dump_db(self):
        "a compressed dump of the test database is created at the expected destination"
        descriptor = {'mysql-database': [self.project_name]}
        results = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(1, len(results['mysql-database']['output']))

        expected_path = os.path.join(self.expected_output_dir, results['mysql-database']['output'][0])
        self.assertTrue(os.path.isfile(expected_path))

    def test_dump_db_fails_if_db_not_found(self):
        descriptor = {'mysql-database': ['pants-party']}
        self.assertRaises(OSError, main.backup, descriptor, conf.WORKING_DIR)


class TestDatabaseRestore(BaseCase):
    def setUp(self):
        self.project_name = '_test'
        self.expected_output_dir = '/tmp/baz/'
        mysql_target.drop(self.project_name)
        mysql_target.create(self.project_name)
        mysql_target.load(self.project_name, os.path.join(self.fixture_dir, 'mysql_test_table.sql'))

    def tearDown(self):
        pass

    # NOTE: if tests are being run in parallel, this test modifies a database that
    # another test may be attempting to read from

    def test_restore_modified_db(self):
        "a database can be backed up, the original database altered, the backup restored."
        descriptor = {'mysql-database': [self.project_name]}
        table_test = partial(mysql_target.fetchone, self.project_name, "select count(*) from table2")

        original_expected_result = {'count(*)': 2}
        self.assertEqual(table_test(), original_expected_result)

        # backup and modify
        main.backup(descriptor, output_dir=self.expected_output_dir)
        mysql_target.mysql_query(self.project_name, "delete from table2")
        self.assertEqual(table_test(), {'count(*)': 0})

        # restore the db, run the test
        main.restore(descriptor, backup_dir=self.expected_output_dir)
        self.assertEqual(table_test(), original_expected_result)

    def test_restore_missing_db(self):
        "a database can be backed up, the original database dropped, the backup restored."
        descriptor = {'mysql-database': [self.project_name]}
        table_test = partial(mysql_target.fetchone, self.project_name, "select count(*) from table2")

        original_expected_result = {'count(*)': 2}
        self.assertEqual(table_test(), original_expected_result)

        # backup and modify
        main.backup(descriptor, output_dir=self.expected_output_dir)
        mysql_target.drop(self.project_name)
        self.assertFalse(mysql_target.dbexists(self.project_name))

        # restore the db, run the test
        expected_results = {'mysql-database': {'output': [(self.project_name, True)]}}
        results = main.restore(descriptor, backup_dir=self.expected_output_dir)
        self.assertEqual(results, expected_results)

        # check data is as it was prior to dump
        self.assertEqual(table_test(), original_expected_result)
