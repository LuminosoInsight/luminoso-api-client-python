from setuptools import setup, find_packages

VERSION = "3.1.0"

classifiers = [
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'Natural Language :: English',
    'Topic :: Scientific/Engineering',
    'Topic :: Text Processing :: Linguistic'
]

GITHUB_URL = 'http://github.com/LuminosoInsight/luminoso-api-client-python'


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="luminoso-api",
    version=VERSION,
    maintainer='Luminoso Technologies, Inc.',
    maintainer_email='info@luminoso.com',
    url=GITHUB_URL,
    download_url='%s/tarball/v%s' % (GITHUB_URL, VERSION),
    platforms=["any"],
    description="Python client library for communicating with the Luminoso REST API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=classifiers,
    packages=find_packages(exclude=('tests',)),
    install_requires=[
        'requests >= 1.2.1, < 3.0',
        'tqdm',
    ],
    tests_require=['pytest', 'requests-mock'],
    entry_points={
        'console_scripts': [
            'lumi-api = luminoso_api.v5_cli:main',
            'lumi-save-token = luminoso_api.save_token:main',
            'lumi-upload = luminoso_api.v5_upload:main',
            'lumi-download = luminoso_api.v5_download:main',
        ]},
)
