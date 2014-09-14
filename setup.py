#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='linkmanager',
    version='1',
    description='etcd-based vxlan tunnel manager',
    author='Lars Kellogg-Stedman',
    author_email='lars@oddbit.com',
    url='http://github.com/larsks/linkmanager',
    install_requires=open('requirements.txt').readlines(),
    packages=find_packages(),
    entry_points = {
        'console_scripts': [
            'linkmanager=linkmanager.main:main',
        ],
    }
)

