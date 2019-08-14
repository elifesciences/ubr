from ubr import utils
from .base import BaseCase


class UtilsTest(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_pairwise(self):
        cases = [
            ([1], []),
            ([1, 2], [(1, 2)]),
            ([1, 2, 3], [(1, 2)]),
            ([1, 2, 3, 4], [(1, 2), (3, 4)]),
        ]
        for given, expected in cases:
            self.assertEqual(list(utils.pairwise(given)), expected)
