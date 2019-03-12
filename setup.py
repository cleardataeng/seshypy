#!/usr/bin/env python
from setuptools import setup, find_packages

with open('VERSION') as version_file:
    version = version_file.read().strip()

with open('seshypy/version.py', 'w') as f:
    f.write("VERSION = '%s'\n" % version)

with open('README.rst') as readme_file:
    readme = readme_file.read()

install_requires = [
    'requests-sigv4>=0.1.4',
    'cachetools>=1.1.6',
    'figgypy>=0.2.0',
    'future',
    'requests>=2.21.0',
    'retrying>=1.3.3',
    'setuptools>=36.5.0'
]

setup(
    name='seshypy',
    version=version,
    description='seshypy makes API Gateway requests and API Gateway clients easy.',
    long_description=readme,
    packages=find_packages(),
    platforms=['all'],
    install_requires=install_requires,
    setup_requires=['pytest-runner'],
    tests_require=[
        'pytest',
        'freezegun',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
