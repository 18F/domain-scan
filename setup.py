"""
setup module for domain-scan

Based on:

- https://packaging.python.org/distributing/
- https://github.com/pypa/sampleproject/blob/master/setup.py
- https://github.com/dhs-ncats/pshtt/blob/master/setup.py
"""

from setuptools import setup, find_packages

setup(
    name='domain-scan',

    # Versions should comply with PEP440
    version='0.1.0-dev1',
    description='lightweight scan pipeline for orchestrating third party tools, at scale and (optionally) using serverless infrastructure',

    # NCATS "homepage"
    url='https://18f.gsa.gov',
    # The project's main homepage
    download_url='https://github.com/18F/domain-scan',

    # Author details
    author='GSA 18F',
    author_email='pulse@cio.gov',

    license='License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',

        # Pick your license as you wish (should match "license" above)
        'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    # What does your project relate to?
    keywords='https best practices web-crawling domain scanning',

    packages=find_packages(),

    install_requires=[
        'strict-rfc3339',
        'publicsuffix',
        'boto3',
        'ipython',
        'sslyze>=1.3.4,<1.4.0',
        'cryptography',
        'pyyaml',
        'requests',
        'google-cloud-bigquery',
        'google-auth-oauthlib'
    ],

    extras_require={
        'test': [
            'pytest'
        ],
    },

    # Conveniently allows one to run the CLI scripts
    scripts=[
        'gather',
        'scan',
    ]
)
