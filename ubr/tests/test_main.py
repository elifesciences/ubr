import mock
from ubr import main
from base import BaseCase

class Main(BaseCase):
    def setUp(self):
        self.patcher = mock.patch('ubr.utils.hostname', return_value='test-machine')
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_parseargs_minimal_args(self):
        given = []
        expected = ['backup', 's3', 'test-machine', []]
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_two_args(self):
        given = ['restore']
        expected = ['restore', 's3', 'test-machine', []]
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_three_args(self):
        given = ['restore', 'file']
        expected = ['restore', 'file', 'test-machine', []]
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_four_args(self):
        given = ['restore', 'file', 'example.org']
        expected = ['restore', 'file', 'example.org', []]
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_five_args(self):
        "optional fifth+ args to specify targets within the descriptor"
        given = ['restore', 'file', 'example.org', 'mysql-database.mydb1']
        expected = ['restore', 'file', 'example.org', ['mysql-database.mydb1']]
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_five_plus_args(self):
        "optional fifth+ args to specify targets within the descriptor"
        given = ['restore', 'file', 'example.org']
        given += [
            'mysql-database.mydb1',
            'files./opt/thing/',
            'mysql-database.mydb2'
        ]
        expected = ['restore', 'file', 'example.org']
        expected += [[
            'mysql-database.mydb1',
            'files./opt/thing/',
            'mysql-database.mydb2',
        ]]
        self.assertEqual(main.parseargs(given), expected)

    def test_download_args(self):
        cases = [
            # download most recent files for this machine from s3
            (['download'], ['download', 's3', 'test-machine', []]),

            # same again
            (['download', 's3'], ['download', 's3', 'test-machine', []]),

            # download most recent files from the prod machine from s3
            (['download', 's3', 'prod--test-machine'], ['download', 's3', 'prod--test-machine', []]),

            # download just the mysql database 'thing' from the prod machine from s3
            (['download', 's3', 'prod--test-machine', 'mysql-database.thing'], ['download', 's3', 'prod--test-machine', ['mysql-database.thing']]),
        ]
        for given, expected in cases:
            actual = main.parseargs(given)
            self.assertEqual(actual, expected, "given %r I expected %r but got %r" % (given, expected, actual))

    def test_download_bad_args(self):
        bad_cases = [
            # downloading a file from filesystem?
            (['download', 'file'], ['download', 'file', 'test-machine', []]),
        ]
        for given, expected in bad_cases:
            self.assertRaises(SystemExit, main.parseargs, given)
