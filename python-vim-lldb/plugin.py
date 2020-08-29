
# Try to import all dependencies, catch and handle the error gracefully if
# it fails.

import import_lldb

try:
    import lldb
    import vim
except ImportError:
    print("Unable to load vim/lldb module, vim-lldb is disabled. Check lldb is available on path with `lldb -P` and codesigned or set lldb_path in .vimrc. See README for setup help.")
    vim.command("let g:lldb_disabled=1")
    pass
else:
    # Everthing went well, so use import to start the plugin controller
    from lldb_controller import *
