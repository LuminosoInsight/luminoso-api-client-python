#!/usr/bin/env python
VERSION = "0.4.3"

from setuptools import setup, find_packages

classifiers = [
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'Natural Language :: English',
    'Topic :: Scientific/Engineering',
    'Topic :: Text Processing :: Linguistic'
]

setup(
    name="luminoso-api",
    version=VERSION,
    maintainer='Luminoso Technologies, Inc.',
    maintainer_email='info@luminoso.com',
    url='http://github.com/LuminosoInsight/luminoso-api-client-python',
    platforms=["any"],
    description="Python client library for communicating with the Luminoso REST API",
    classifiers=classifiers,
    packages=find_packages(),
    install_requires=['requests-transition', 'chardet', 'ftfy'],
    entry_points={
        'console_scripts': [
            'lumi-upload = luminoso_api.upload:main',
            'lumi-json-stream = luminoso_api.json_stream:main',
        ]},
)
