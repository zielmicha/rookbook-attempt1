#!/bin/bash
set -e
#pytype --config pytype.config
nosetests3
python3 -m doctest rookcore/reactive.py
