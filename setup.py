#!/usr/bin/env python

from setuptools import setup, find_packages

with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(
    name='Storitch',
    version='0.0.0',
    author='Thomas Erlang',
    author_email='thomas@erlang.dk',
    url='https://tesoft.dk/storitch',
    description='Simple file storage system',
    long_description=__doc__,
    package_dir={'': 'src'},
    packages=find_packages('src'),
    zip_safe=False,
    install_requires=install_requires,
    license=None,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'storitch = storitch.app:main',
        ],
    },
    classifiers=[],
)