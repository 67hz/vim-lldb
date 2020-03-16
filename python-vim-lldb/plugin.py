
# Try to import all dependencies, catch and handle the error gracefully if
# it fails.

import import_lldb

try:
    import lldb
    import vim
except ImportError:
    sys.stderr.write(
            "Unable to load vim/lldb module. Check lldb is on the path and available (or LLDB is set) and that script is invoked inside Vim with :pyxfile. See :help pyxfile for more info.")
    pass
else:
    # Everthing went well, so use import to start the plugin controller
    from lldb_controller import *
