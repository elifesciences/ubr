import os
import mock
from ubr import conf
from .base import BaseCase

class One(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_conf_var_default(self):
        expected = 'bup'
        actual = conf.var('UBR_FOO', 'foo.bar', 'bup')
        self.assertEqual(expected, actual)

    def test_conf_var_cfg(self):
        expected = 'baz'
        with mock.patch('ubr.conf.cfg', return_value=expected) as mockobj:
            actual = conf.var('UBR_FOO', 'foo.bar', 'bup')
            self.assertEqual(expected, actual)
            self.assertEqual(mockobj.call_count, 1)

    def test_conf_var_envvar(self):
        try:
            expected = 'baz'
            os.environ['UBR_FOO'] = expected
            actual = conf.var('UBR_FOO', 'foo.bar', 'bup')
            self.assertEqual(expected, actual)
        finally:
            os.environ['UBR_FOO'] = ''
