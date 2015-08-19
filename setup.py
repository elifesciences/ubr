from setuptools import setup

MODULE = 'ubr' # name of the subdirectory your code resides in
NAME = 'Universal Backup-Restore' # project name
AUTHORS = ["Luke Skibinski <l.skibinski@elifesciences.org>"] # list of all contributing authors
LICENCE = 'GPLv3' # licence short name
COPYRIGHT = 'eLife Sciences' # copyright owner
VERSION = '2015.5.27' # some sort of natural ordering key
DESCRIPTION = 'A small library that reads backup "descriptors" in YAML format.'


def groupby(func, lst):
    x, y = [], []
    for val in lst:
        (x if func(val) else y).append(val)
    return x, y

def requirements():
    requisites = open('requirements.txt', 'r').read().splitlines()
    pypi, non_pypi = groupby(lambda r: not r.startswith('-e '), requisites)
    non_pypi = map(lambda v: v[len('-e '):], non_pypi)
    return {
        'install_requires': pypi,
        'dependency_links': non_pypi,
    }

setup(
    name = NAME,
    version = VERSION,
    description = DESCRIPTION,
    long_description = open('README.md', 'r').read(),
    packages = [MODULE],
    license = open('LICENCE.txt', 'r').read(),
    **requirements()
)
