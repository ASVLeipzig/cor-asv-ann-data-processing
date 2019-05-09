# -*- coding: utf-8 -*-
"""
Installs the executable tesserocr-batch
"""
import codecs
from setuptools import setup

with codecs.open('README.md', encoding='utf-8') as file:
    README = file.read()

setup(
    name='data-processing',
    version='0.1',
    description='various tools for data processing',
    long_description=README,
    author='Robert Sachunsky',
    author_email='sachunsky@informatik.uni-leipzig.de',
    license='Apache License 2.0',
    install_requires=[
        'click',
        'tesserocr >= 2.3.1',
        'ocrd >= 1.0.0b8',
        'ocrd_tesserocr',
        'cis-ocrd@git+ssh://git@github.com/cisocrgroup/cis-ocrd-py@dev',
        'pyphen',
    ],
    entry_points={
        'console_scripts': [
            'tesserocr-batch=tesserocr_batch:process',
            'prob2pkl=prob2pkl:cli',
            'confmat2pkl=confmat2pkl:cli',
            'ocrd-gt2pkl=ocrd_gt2pkl:cli',
            'dta-txt2gt=dta_txt2gt:cli',
        ]
    },
)
