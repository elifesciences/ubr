from ubr import s3
from base import BaseCase

class UtilsTest(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_filterer(self):
        input = [
            'civicrm/201507/20150731_ip-10-0-2-118_230108-ELIFECIVICRM-mysql.gz',
            'civicrm/201507/20150731_ip-10-0-2-118_230111-ELIFEDRUPAL-mysql.gz',
            'civicrm/201508/20150731_ip-10-0-2-118_230115-archive.tar.gz',

            'civicrm/201508/20150801_ip-10-0-2-118_230108-ELIFECIVICRM-mysql.gz',
            'civicrm/201508/20150801_ip-10-0-2-118_230112-ELIFEDRUPAL-mysql.gz',
            'civicrm/201508/20150801_ip-10-0-2-118_230115-archive.tar.gz',
        ]

        project = "civicrm"
        host = "ip-10-0-2-118"
        filename = "archive.tar.gz"

        expected_results = [
            'civicrm/201508/20150731_ip-10-0-2-118_230115-archive.tar.gz',
            'civicrm/201508/20150801_ip-10-0-2-118_230115-archive.tar.gz',
        ]

        results = s3.filterasf(input, project, host, filename)
        self.assertEqual(results, expected_results)
