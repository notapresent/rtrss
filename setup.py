"""
RTRSS
-----

RSS feeds for popular bittorrent tracker

"""
from setuptools import setup


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
    install_requires=[
        'Flask-SQLAlchemy==2.0',
        'lxml==3.4.1',
        'psycopg2==2.5.4',
        'python-dateutil==2.3',
        'requests==2.5.1',
        'schedule==0.3.1',
        'tzlocal==1.1.2',
        'bencode==1.0'
    ],
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
