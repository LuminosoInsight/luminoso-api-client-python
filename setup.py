#!/usr/bin/env python
VERSION = "0.4.7"

from setuptools import setup, find_packages

classifiers = [
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'Natural Language :: English',
    'Topic :: Scientific/Engineering',
    'Topic :: Text Processing :: Linguistic'
]

GITHUB_URL = 'http://github.com/LuminosoInsight/luminoso-api-client-python'

setup(
    name="luminoso-api",
    version=VERSION,
    maintainer='Luminoso Technologies, Inc.',
    maintainer_email='info@luminoso.com',
    url=GITHUB_URL,
    download_url='%s/tarball/v%s' % (GITHUB_URL, VERSION),
    platforms=["any"],
    description="Python client library for communicating with the Luminoso REST API",
    classifiers=classifiers,
    packages=find_packages(),
    install_requires=[
        'requests >= 1.2.1, < 3.0',
        'ftfy >= 3.3, < 5',
    ],
    entry_points={
        'console_scripts': [
            'lumi-upload = luminoso_api.upload:main',
            'lumi-json-stream = luminoso_api.json_stream:main',
        ]},
)
