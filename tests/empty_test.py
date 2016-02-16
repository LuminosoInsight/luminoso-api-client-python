from __future__ import print_function, unicode_literals
from io import open

def test_readme():
    # A blank test, to satisfy automated testing
    print(open('README.md', encoding='utf-8').read())
