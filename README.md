vim-lldb
========

LLDB debugging in Vim.


Installation
------------

The recommended install procedure for any plugin is to use Vim's native package manager.
See `:help packages` for details 


System Requirements
-------------------

- Vim 8.2 or above
- Vim compiled with '+terminal' support
- Have `LLDB` installed and built against a [matching version of Python](#verifying-python-support)*


vim-lldb Commands
-----------------

All `LLDB` are supported in vim-lldb.

For a complete list of commands, see [gdb to lldb map](https://lldb.llvm.org/use/map.html)

vim-lldb offers some convenience commands for easy mapping.

| Command           | List                                                                    |
| ---               | ---                                                                     |
| `:help lldb`      | plugin specific documentation                                           |
| `:Break`          | Toggle breakpoint under cursor                                |


Customization
-------------

```vim
" set python interpereter path - this is used to launch lldb
let g:lldb_python_interpreter_path = 'usr/bin/python'
```

```vim
" enable lldb, default is 1 {enable}, 0 {disable}
let g:lldb_enable = 1
```


Verifying Python Support
------------------------

This plugin leverages the `LLDB` module which requires Python support on the host system. Vim does not need to be
compiled with Python support for the plugin to work. The plugin will launch the debugger instance in a built-in terminal using `python` as the interpreter. This should be [overridden](#customization) to point to the host's Python path if it differs.


If Vim warns that it is unable to load vim-lldb on launch, there may be mismatched versions of Python running between `LLDB` and the system Python interpreter. Versions must match exactly. If LLDB was compiled for Python2, the interpreter path must point to the exact version of Python2 `LLDB` was compiled against.
 

Verify LLDB's version of Python by launching the Python interpreter in LLDB: 

    $> lldb -b -o "script import sys; print(sys.version)"
    3.7.6 (default, ...)


If Python versions are mismatched, either recompile Python to match the exact version as LLDB or vice-versa. See [lldb caveats](https://lldb.llvm.org/resources/caveats.html) for details.
