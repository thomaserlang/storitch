#!/usr/bin/env python

from setuptools import setup, find_packages

with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(
    name='Storitch',
    version='1.0.5',
    author='Thomas Erlang',
    author_email='thomas@erlang.dk',
    url='https://github.com/thomaserlang/storitch',
    description='File upload and thumbnail generator',
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    install_requires=install_requires,
    license=None,
    include_package_data=True,
    classifiers=[],
    entry_points={
        'console_scripts': [
            'storitch = storitch.runner:app',
        ],
    },
)