# -*- coding: utf-8 -*-
"""
Installs the executable tesserocr-batch
"""
from setuptools import setup

setup(
    name='tesserocr-batch',
    version='0.1',
    description='Tesseract CLI for batch processing',
    author='Robert Sachunsky',
    author_email='sachunsky@informatik.uni-leipzig.de',
    license='Apache License 2.0',
    install_requires=[
        'tesserocr >= 2.3.0',
        'click',
    ],
    entry_points={
        'console_scripts': [
            'tesserocr-batch=tesserocr_batch:process',
        ]
    },
)
