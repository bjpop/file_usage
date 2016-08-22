#!/usr/bin/env python

from distutils.core import setup

LONG_DESCRIPTION = '''Explore file usage in a top-down manner'''

setup(
    name='file_usage',
    version='1.0.0',
    author='Bernie Pope',
    author_email='bjpope@unimelb.edu.au',
    packages=['file_usage'],
    package_dir={'file_usage': 'file_usage'},
    entry_points={
        'console_scripts': ['file_usage = file_usage.file_usage:main']
    },
    url='https://github.com/bjpop/file_usage',
    license='LICENSE',
    description=('Explore file usage in a top-down manner'),
    long_description=(LONG_DESCRIPTION),
    install_requires=["termcolor==1.1.0"],
)
