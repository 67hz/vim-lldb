vim-lldb
========

### LLDB debugging in Vim

This version of vim-lldb supports both Python2 and Python3. This was forked from LLVM tools which only supports Python2. It is currently under development so there will be bugs. If you see something, say something.


Installation
------------

### Using [vim-plug](https://github.com/junegunn/vim-plug)

```vim
Plug '67hz/vim-lldb'
```

### Using [vundle](https://github.com/VundleVim/Vundle.Vim)

```vim
Plugin '67hz/vim-lldb'
```

- Make sure to use Vim 8.2 or above
- Have Python or Python3 support in Vim

vim-lldb Commands
--------

| Command           | List                                                                    |
| ---               | ---                                                                     |
| `:Lunbind`        | Unbind LLDB (*temp fix: use only if LLDB acts up)                       |
| `:Lbind`          | Rebind above                                                            |
| `:help lldb`      | plugin specific documentation                                           |
| `:Lhelp`          | LLDB's built-in help system (i.e lldb 'help' command)                   |
|  `:Lscript help (lldb)` | Complete LLDB Python API reference                                |
| `:L<tab>`         | tab completion through all LLDB commands                                |



LLDB Commands
-------------

All LLDB commands available through `:L<lldb_command>`.


Here are key commands:


| Command           | List                                                                    |
| ---               | ---                                                                     |
| `:Ltarget file`   | specify target file                                                     |
| `:Lbr`            | set breakpoint under cursor                                             |


[gdb to lldb map](https://lldb.llvm.org/use/map.html)


Customization
-------------

### Global options

If a custom version of LLDB is compiled to match and it is not the same as the system default, link the matching `LLDB` to vim.
To set a custom path for `LLDB`, add the following to `vimrc`:

```vim
" add path to lldb
let g:lldb_path="/absolute/path/to/lldb"
```

Enable/disable

```vim
" enable llvm, set to 0 to disable
let g:enable_llvm = 1
```



Verifying Python Support
------------------------

This plugin leverages the `LLDB` module which requires python support in Vim. Vim's python version with must match `LLDB`'s python interpreter version.

To verify Vim's python support, run:

    vim --version | grep python

The output must contain either `+python` or `+python3`

The above command displays the major version of vim. It is possible that a different minor/patch version is running between `LLDB` and python. To verify Vim's exact python version, launch vim and run: 
 
    : pyx << EOF
     import sys
     print(sys.version)
     EOF
     
     " verify this output matches lldb's
     3.7.6 (default, ...)



Verify LLDB's python version by launching the python interpreter in LLDB: 

    $> lldb
    (lldb) script
    Python Interactive Interpreter
    >>> import sys
    >>> print(svs.version)
    3.7.6 (default, ...)


If versions are mismatched, either recompile Vim to match the same version as LLDB or vice-versa.

See **Customization** for specifying lldb path in `vimrc`.


### @TODOs

* better instructions for compiling Vim/Python/LLDB to work in harmony
* check for vim/lldb python versions match before importing lldb
* Look into term-debug and potential feature parity with gdb
