#!/usr/bin/env python3
"""
Redirect intermediate build artefacts to Build/none/any instead of the default
./build/ directory that setuptools would otherwise create in the project root.

Once pyproject.toml / setuptools add native support for build-base configuration,
this file can be removed and configuration moved entirely to pyproject.toml.

Reference: PEP 517/518 (pyproject.toml standard)
"""
from setuptools import setup
import distutils.command.build
import os


class BuildCommand(distutils.command.build.build):
    """Direct intermediate build files to Build/none/any."""

    def initialize_options(self):
        distutils.command.build.build.initialize_options(self)
        self.build_base = 'Build/none/any'


setup_opts: dict = {"cmdclass": {"build": BuildCommand}}

# Inject the bif buildid as the wheel build number so the filename carries it.
if (buildid := os.getenv('BIF_BUILD_BUILDID', '').strip()):
    setup_opts['options'] = {
        'bdist_wheel': {
            'build_number': buildid
        }
    }

setup(**setup_opts)
