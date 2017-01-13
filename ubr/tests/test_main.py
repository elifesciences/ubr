import mock
from ubr.conf import logging
from ubr import main
from base import BaseCase
from logger_test import LogTestCase

class Main(BaseCase):
    def setUp(self):
        mock.patch('ubr.utils.hostname', return_value='test-machine').start()

    def tearDown(self):
        pass

    def test_parseargs_minimal_args(self):
        given = ['/etc/ubr/foo-backup.yaml']
        expected = ['/etc/ubr/foo-backup.yaml', 'backup', 's3', 'test-machine', []]
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_two_args(self):
        given = ['/etc/ubr/foo-backup.yaml', 'restore']
        expected = ['/etc/ubr/foo-backup.yaml', 'restore', 's3', 'test-machine', []]
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_three_args(self):
        given = ['/etc/ubr/foo-backup.yaml', 'restore', 'file']
        expected = ['/etc/ubr/foo-backup.yaml', 'restore', 'file', 'test-machine', []]
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_four_args(self):
        given = ['/etc/ubr/foo-backup.yaml', 'restore', 'file', 'example.org']
        expected = ['/etc/ubr/foo-backup.yaml', 'restore', 'file', 'example.org', []]
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_five_args(self):
        "optional fifth+ args to specify targets within the descriptor"
        given = ['/etc/ubr/foo-backup.yaml', 'restore', 'file', 'example.org', 'mysql-database.mydb1']
        expected = ['/etc/ubr/foo-backup.yaml', 'restore', 'file', 'example.org', ['mysql-database.mydb1']]
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_five_plus_args(self):
        "optional fifth+ args to specify targets within the descriptor"
        given = ['/etc/ubr/foo-backup.yaml', 'restore', 'file', 'example.org']
        given += [
            'mysql-database.mydb1',
            'files./opt/thing/',
            'mysql-database.mydb2'
        ]
        expected = ['/etc/ubr/foo-backup.yaml', 'restore', 'file', 'example.org']
        expected += [[
            'mysql-database.mydb1',
            'files./opt/thing/',
            'mysql-database.mydb2',
        ]]
        self.assertEqual(main.parseargs(given), expected)

class Logging(BaseCase, LogTestCase):
    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_failure_is_logged_1(self):
        "calling the app with bad arguments issues a warning"
        with self.assertLogs(main.__name__, level=logging.INFO) as log:
            try:
                main.main("asdfasdfasdfsafsda") # I don't understand, Dave
            except SystemExit:
                pass

            expected = [
                ('WARNING', 'invalid arguments')
            ]
            self.assertEqual(expected, log.output)
