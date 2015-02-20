"""
RTRSS
-----

RSS feeds for popular bittorrent tracker

"""
from setuptools import setup

with open('reqs/production.txt') as f:
    _requirements = f.read().splitlines()

with open('reqs/deplinks.txt') as f:
    _deplinks = f.read().splitlines()

setup(
    name='rtrss',
    version='0.3',
    author='notapresent',
    author_email='notapresent@gmail.com',
    url='https://github.com/notapresent/rtrss',
    description='RSS feeds for popular bittorrent tracker',
    long_description=__doc__,
    license='Apache 2.0',
    download_url='https://github.com/notapresent/rtrss/archive/master.zip',
    packages=['rtrss'],
    install_requires=_requirements,
    dependency_links=_deplinks,
    entry_points={
        'console_scripts': [
            'rtrssmgr = rtrss.worker:main',
        ],
    },

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Framework :: Flask',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ]
)
