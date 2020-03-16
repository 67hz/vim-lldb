
# Try to import all dependencies, catch and handle the error gracefully if
# it fails.

import import_lldb

try:
    import lldb
    import vim
except ImportError:
    sys.stderr.write(
            "Unable to load vim/lldb module, vim-lldb is disabled. Check lldb is available on path with `lldb -P` or set lldb_path in .vimrc. See README for info on setting up lldb.")
    pass
else:
    # Everthing went well, so use import to start the plugin controller
    from lldb_controller import *
