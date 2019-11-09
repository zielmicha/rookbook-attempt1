#!/bin/bash
set -e
pytype --config pytype.config
nosetests3
