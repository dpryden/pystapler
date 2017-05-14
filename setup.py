"""Setup script for pystapler framework."""

from setuptools import setup

setup(
    name='pystapler',
    version='0.1',
    description='Pystapler application server framework',
    author='Daniel Pryden',
    author_email='daniel@pryden.net',
    license='MIT',
    packages=['pystapler'],
    install_requires=[
        'decorator>=4.0.11',
        'six>=1.10.0',
        'werkzeug>=0.11',
    ],
)
