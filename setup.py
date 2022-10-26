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
    version='0.3.5',
    packages=['s3_browser'],
    entry_points={
        'console_scripts': [
            's3-browser=s3_browser.cli:main'
        ]
    },
    install_requires=['boto3>=1.9.0', 'python-magic>=0.4.27'],
    python_requires='>=3.2',
    long_description=readme_content(),
    long_description_content_type='text/markdown',
    keywords='aws s3 browser cli interactive prompt s3-browser',
    author='Rob Moore',
    author_email='giftiger.wunsch@xantoria.com',
    license='MIT',
    url='https://github.com/giftig/s3-browser/',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Internet',
        'Topic :: Terminals',
        'Topic :: Utilities'
    ]
)
