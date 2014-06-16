# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from luminoso_api.json_stream import open_json_or_csv_somehow as openstuff
from nose.tools import eq_ as eq
import os

reference = None
EXAMPLE_DIR = os.path.dirname(__file__) + '/examples'


def canonical_dicts(seq):
    return [sorted(entry.items()) for entry in seq]


def test_json_loading():
    reference = canonical_dicts(openstuff(EXAMPLE_DIR + '/reference.jsons'))

    # Load the same data from a standard JSON file containing a list
    loaded = canonical_dicts(openstuff(EXAMPLE_DIR + '/example1.json'))
    eq(loaded, reference)

    # Load exactly the same file, except this time it claims slightly
    # incorrectly to be .json instead of .jsons
    loaded2 = canonical_dicts(openstuff(EXAMPLE_DIR + '/example1.stream.json'))
    eq(loaded2, reference)

    unbroken = list(openstuff(EXAMPLE_DIR + '/linebreaks.jsons'))
    eq(len(unbroken), 1)


def test_csv_loading():
    reference = canonical_dicts(openstuff(EXAMPLE_DIR + '/utf8.csv'))
    eq(reference[0][0][1], "This — should be an em dash")
    eq(reference[1][0][1], 'This one\'s got "smart" quotes')
    eq(reference[2][0][1], "HTML escaping makes me mad >:(")

    loaded = canonical_dicts(openstuff(EXAMPLE_DIR + '/windows1252.csv'))
    eq(loaded, reference)

    loaded2 = canonical_dicts(openstuff(EXAMPLE_DIR + '/macroman.csv'))
    eq(loaded2, reference)
