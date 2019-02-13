from setuptools import setup

setup(
    name='s3_browser',
    version='0.1',
    packages=['s3_browser'],
    entry_points={
        'console_scripts': [
            's3-browser=s3_browser.cli:main'
        ]
    },
    install_requires=['boto3>=1.9.0']
)
