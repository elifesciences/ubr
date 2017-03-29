import os
import glob
from ubr import main, tgz_target
from base import BaseCase

class TestTarredGzippedBackup(BaseCase):
    def setUp(self):
        self.expected_output_dir = '/tmp/foo'

    def tearDown(self):
        os.system('rm /tmp/foo/archive.*.tar.gz')

    def test_simple_tgz(self):
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        paths = [fixture, os.path.join(self.fixture_dir, '*/**')]
        descriptor = {'tar-gzipped': paths}
        output = main.backup(descriptor, output_dir=self.expected_output_dir)

        filename = tgz_target.filename_for_paths(paths)
        expected_output = {
            'tar-gzipped': {
                'output': [os.path.join(self.expected_output_dir, filename + '.tar.gz')]}}
        self.assertEqual(output, expected_output)
        # test all of the files exist
        for path in output['tar-gzipped']['output']:
            self.assertTrue(os.path.exists(path))

    def test_tgz_returns_a_list_of_outputs(self):
        "the tgz target returns a list for it's 'output' result. all targets must return a list"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        descriptor = {'tar-gzipped': [fixture]}
        results = main.backup(descriptor, output_dir=self.expected_output_dir)
        self.assertEqual(1, len(results['tar-gzipped']['output']))

    def test_bad_backup_target_doesnt_prevent_subsequent(self):
        "if a backup target fails to create it's backup, it shouldn't stop other targets from being backed up"
        descriptor = {
            'tar-gzipped': [
                '/does/not/exist/',
            ]
        }
        results = main.backup(descriptor)
        expected = []
        self.assertEqual(expected, results['tar-gzipped']['output'])


class TestTarredGzippedRestore(BaseCase):
    def setUp(self):
        self.expected_output_dir = '/tmp/baz'

    def tearDown(self):
        archive_files = glob.glob(os.path.join(self.expected_output_dir, 'archive-*'))
        map(lambda path: os.system('rm ' + path), archive_files)

    def test_tgz_restore(self):
        "tar-gzipped target unpacks the backup and restores the files"
        fixture = os.path.join(self.fixture_dir, 'img1.png')
        paths = [fixture]
        descriptor = {'tar-gzipped': paths}
        main.backup(descriptor, output_dir=self.expected_output_dir)

        # ensure an archive was created
        filename = tgz_target.filename_for_paths(paths)
        expected_path = os.path.join(self.expected_output_dir, filename + '.tar.gz')
        self.assertTrue(os.path.isfile(expected_path))

        # ensure we get the expected output
        expected_results = {
            'tar-gzipped': {
                # a list of absolute paths-to-files (single file in our case)
                'output': [(os.path.abspath(fixture), True)]
            }
        }
        results = main.restore(descriptor, backup_dir=self.expected_output_dir)
        self.assertEqual(results, expected_results)
