import mock
from ubr import main
from base import BaseCase

class Main(BaseCase):
    def setUp(self):
        mock.patch('ubr.utils.hostname', return_value='test-machine').start()

    def tearDown(self):
        pass

    def test_parseargs_minimal_args(self):
        given = ['/etc/ubr/foo-backup.yaml']
        expected = ['/etc/ubr/foo-backup.yaml', 'backup', 's3', 'test-machine']
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_two_args(self):
        given = ['/etc/ubr/foo-backup.yaml', 'restore']
        expected = ['/etc/ubr/foo-backup.yaml', 'restore', 's3', 'test-machine']
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_three_args(self):
        given = ['/etc/ubr/foo-backup.yaml', 'restore', 'file']
        expected = ['/etc/ubr/foo-backup.yaml', 'restore', 'file', 'test-machine']
        self.assertEqual(main.parseargs(given), expected)

    def test_parseargs_four_args(self):
        given = ['/etc/ubr/foo-backup.yaml', 'restore', 'file', 'example.org']
        expected = ['/etc/ubr/foo-backup.yaml', 'restore', 'file', 'example.org']
        self.assertEqual(main.parseargs(given), expected)
