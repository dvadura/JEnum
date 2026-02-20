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
import pathlib

# --------------------------------------------------------------------------------------------------
# GitKeep adds .gitkeep into any dir you specify. Typically used for the .deps dir in clang builds.
# Since the .d files stored in .deps are inferred and pre-made they are cleaned the same way. Thus,
# a bif clean will remove them, and keep the .gitkeep in the dir. Which is what you want if your intent
# is to persist the dir in a git repository.
# --------------------------------------------------------------------------------------------------
class GitKeep(PluginBase):
    GIT_KEEP_FILE = '.gitkeep'

    def __init__(self):
        pass

    def eval(self, *args, **kwargs):
        if not args or not args[0]:
            return None

        path: pathlib.Path = pathlib.Path(args[0]) / GitKeep.GIT_KEEP_FILE
        if path.is_file():
            return None

        path.touch(exist_ok=True)
        return f'Created {GitKeep.GIT_KEEP_FILE} in {args[0]}'
