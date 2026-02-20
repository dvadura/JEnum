# --------------------------------------------------------------------------------------------------
# Sample plugin.
#
# To make a plugin, import PluginBase, and create a class that implements eval as below.
# Because Bif is compiled with nuitka, by default, you can import any python builtin package
# and any of the packages listed in the bootstrap.py file in Bif Source tree.
#
# Make sure that you check the Source for your version to see the latest list of included
# packages.
#
# The following non-builtin packages are guaranteed to be included:
#
#   - typingextensions
#   - pytest
#   - argparse
#   - pathlib
#   - pyjson5
#   - pyaml
#   - wcmatch
#   - nuitka
#   - lark
#   - rich
#
# --------------------------------------------------------------------------------------------------
import pytest

from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

from plugins import PluginBase

class Pytest(PluginBase):
    def __init__(self):
        pass

    def eval(self, *args, **kwargs):
        tmp_stdout = StringIO()
        tmp_stderr = StringIO()
        with redirect_stdout(tmp_stdout), redirect_stderr(tmp_stderr):
            result = pytest.main(list(*args))
        return tmp_stdout.getvalue() + tmp_stderr.getvalue()
