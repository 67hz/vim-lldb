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
- Vim compiled with `+terminal` support
- Have `LLDB` installed and built against a [matching version of Python on the host](#verifying-python-support)


vim-lldb Commands
-----------------

For a complete list of commands, see [gdb to lldb map](https://lldb.llvm.org/use/map.html)

vim-lldb offers some convenience commands for easy mapping.

| Command           | List                                                                    |
| ---               | ---                                                                     |
| `:help lldb`      | plugin specific documentation                                           |
| `:LBreak`          | Toggle breakpoint under cursor                                |
| `:LStep`          | Step |
| `:LNext`          | Next
| `:LInfo`          | Display system info (useful for troubleshooting setup)         | 


Customization
-------------

```vim
" set python interpereter path - this is used to launch lldb
let g:lldb_python_interpreter_path = 'usr/bin/python'
```

'''vim
" set path to lldb executable
let g:lldb_path = 'usr/local/bin/lldb'
'''

```vim
" enable lldb, default is 1 {enable}, 0 {disable}
let g:lldb_enable = 1
```


Verifying Python Support
------------------------

This plugin leverages the `LLDB` module which requires Python support on the host system. The plugin will launch the debugger instance in a built-in terminal using LLDB's `Python path as the interpreter. 

Internally, the plugin uses the result of:

    $> lldb -b -o "script import sys; print(sys.executable)"

    (lldb) script import sys; print(sys.executable)
    /usr/bin/python3

to determine the path to the Python interpreter.  If `LLDB` is not available on the host via `lldb`, override `g:lldb_path` in your `.vimrc` accordingly.

Additionally, the `g:lldb_python_interpreter_path` can be [overridden](#customization) to point to the host's Python path.


If Vim warns that it is unable to load vim-lldb on launch, there may be mismatched versions of Python running between `LLDB` and the system Python interpreter. Versions must match exactly.


### Troubleshooting:

Get information about the host paths to Python and LLDB:

```vim
:call LInfo
```

Verify LLDB's Python path from the shell:

    $> lldb -b -o "script import sys; print(sys.executable)"
    (lldb) script import sys; print(sys.executable)
    /usr/bin/python3

In the above example output, `/usr/bin/python3` is the path `LLDB` requires to launch. In this setup, the proper `.vimrc` setting 
will allow LLDB to launch properly:

```vim
  let g:lldb_python_interpreter_path='/usr/bin/python3'
```

If Python versions are mismatched, either recompile Python to match the exact version as LLDB or vice-versa. See [lldb caveats](https://lldb.llvm.org/resources/caveats.html) for details.
