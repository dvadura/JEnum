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
from plugins import PluginBase

class Echo(PluginBase):
    def __init__(self):
        pass

    def eval(self, *args, **kwargs):
        return ''.join(args)
