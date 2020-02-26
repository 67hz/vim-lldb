vim-lldb
========

### LLDB debugging in Vim

This version of vim-lldb supports Python2 and Python3. This was forked from LLVM tools which only supports Python2. It is currently under development so there will be bugs. If you see something, say something.


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
| `:Lscript help (lldb)` | Complete LLDB Python API reference                                |
| `:L<tab>`         | tab completion through all LLDB commands                                |



LLDB Commands
-------------

All LLDB commands are available through `:L<lldb_command>`. Using lldb's documentation at `:Lhelp` with `:L<tab>` tab completion is a good place to start. Remember to prepend all commands with `:L`.
For example:

```vim
" set a target file
:Ltarget ./path/to/file
" set a breakpoint under cursor
:Lbreakpoint
" run debugger
:Lrun
```

Here are a some example commands:


| Command           | List                                                                    |
| ---               | ---                                                                     |
| `:Ltarget file`   | specify target file                                                     |
| `:Lbr`            | set breakpoint under cursor                                             |
| `:Lrun`           | run                                                                     |


[gdb to lldb map](https://lldb.llvm.org/use/map.html)


Customization
-------------

### Global options

To set a custom path for `lldb`, add the following to `vimrc`:

```vim
" add path to lldb
let g:lldb_path="/absolute/path/to/lldb"
```

Enable/disable plugin:

```vim
" enable lldb, set to 0 to disable
let g:enable_lldb = 1
```



Verifying Python Support
------------------------

This plugin leverages the `LLDB` module which requires python support in vim. Vim's python version must match `LLDB`'s python interpreter version.

To verify Vim's python support, run:

    vim --version | grep python

The output must contain either `+python` or `+python3`

The above command displays the major version of vim. It is possible that a different minor/patch version is running between `LLDB` and python. To verify vim's exact python version, launch vim and run: 
 
     :pyx << EOF
     import sys
     print(sys.version)
     EOF
     
     " verify this output matches lldb's
     3.7.6 (default, ...)



Verify LLDB's version of python by launching the python interpreter in LLDB: 

    $> lldb
    (lldb) script
    Python Interactive Interpreter
    >>> import sys
    >>> print(svs.version)
    3.7.6 (default, ...)


If python versions are mismatched, either recompile Vim to match the same version as LLDB or vice-versa.

See **Customization** for specifying lldb path in `vimrc`.


### @TODOs

* add customization options
* move style settings to separate data structure(s) and centralize
  * customizable panes
    * dis view: customize number of instructions to disassemble
* shorter commands can be ambiguous, e.g. Lb 89
* fix arg separations for variadics, e.g. Lbreakpoint 83
* clean up output in panes
* allow custom theming and remove hard-coded styles
* handle strings as non-bytes for Python3
* better instructions for compiling Vim/Python/LLDB to work in harmony
* check for vim/lldb python versions match before importing lldb
* Look into term-debug and potential feature parity with gdb
