
# Try to import all dependencies, catch and handle the error gracefully if
# it fails.

#import vim
import lldb_path
import subprocess

lldb_path.update_sys_path()

def launchLLDB():
    print("launch lldb subp")
    proc = subprocess.Popen(['python', ' lldb_server.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)


try:
    import lldb
except ImportError:
    #vim.command("let g:lldb_disabled=1")
    print("Unable to load vim/lldb module, vim-lldb is disabled. Check lldb is available on path with `lldb -P` and codesigned or set lldb_path in .vimrc. See README for setup help.")
    pass
else:
    # Everthing went well, so use import to start the plugin controller
    from lldb_controller import *
    #sbd = lldb.SBDebugger.Create()
    pass
