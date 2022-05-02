from ubr import utils


def test_pairwise():
    cases = [
        ([1], []),
        ([1, 2], [(1, 2)]),
        ([1, 2, 3], [(1, 2)]),
        ([1, 2, 3, 4], [(1, 2), (3, 4)]),
    ]
    for given, expected in cases:
        assert list(utils.pairwise(given)) == expected


def test_common_prefix():
    cases = [
        (["/"], "/"),
        (["/a", "/"], None),  # root paths not handled so well :(
        (["/a", "/b"], None),
        (["/a", "/b"], None),
        (["/a", "/a"], "/a"),
        (["/a/b/c/d", "/a"], "/a"),
        (["/a", "/a/b/c/d"], "/a"),
        (["/a/b", "/a/c", "/a/d", "/a/e"], "/a"),
    ]
    for path_list, expected in cases:
        assert utils.common_prefix(path_list) == expected
