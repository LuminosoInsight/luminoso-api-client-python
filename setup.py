#!/usr/bin/env python
VERSION = "0.3.2"

from setuptools import setup, find_packages

classifiers=[
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'Natural Language :: English',
    'Topic :: Scientific/Engineering',
    'Topic :: Text Processing :: Linguistic']

setup(
    name="luminoso-api",
    version = VERSION,
    maintainer='Luminoso, LLC',
    maintainer_email='team@lumino.so',
    url = 'http://github.com/LuminosoInsight/luminoso-api-client-python',
    platforms = ["any"],
    description = "Python client library for communicating with the Luminoso REST API",
    classifiers = classifiers,
    packages=find_packages(),
    install_requires=['requests>=0.13.5',
                     ],
    entry_points={
        'console_scripts': [
            ]},
)
