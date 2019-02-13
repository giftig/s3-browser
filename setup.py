#!/usr/bin/env python3
import os
from setuptools import setup


def readme_content():
    dir = os.path.abspath(os.path.dirname(__file__))
    desc = None
    with open(os.path.join(dir, 'README.md'), 'r') as f:
        desc = f.read()

    return desc

setup(
    name='s3_browser',
    version='0.1',
    packages=['s3_browser'],
    entry_points={
        'console_scripts': [
            's3-browser=s3_browser.cli:main'
        ]
    },
    install_requires=['boto3>=1.9.0'],
    long_description=readme_content(),
    long_description_content_type='text/markdown'
)
