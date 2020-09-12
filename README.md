vim-lldb
========

LLDB debugging in Vim.


Installation
------------

### Using Vim's native package manager is recommended

See `:help packages` for details 

### Using [vim-plug](https://github.com/junegunn/vim-plug)

```vim
Plug 'lldb-tools/vim-lldb'
```

### Using [vundle](https://github.com/VundleVim/Vundle.Vim)

```vim
Plugin 'lldb-tools/vim-lldb'
```

System Requirements
-------------------

- Vim 8.2 or above
- Have lldb installed against a [matching version of Python](#verifying-python-support)*


vim-lldb Commands
--------

| Command           | List                                                                    |
| ---               | ---                                                                     |
| `:help lldb`      | plugin specific documentation                                           |
| `:Lhelp`          | LLDB's built-in help system (i.e lldb 'help' command)                   |
| `:Lscript help (lldb)` | Complete LLDB Python API reference                                |
| `:L<tab>`         | tab completion through all LLDB commands                                |



LLDB Commands
-------------

Example commands:


| Command           | Function                                                                    |
| ---               | ---                                                                     |
| `:Ltarget file`   | specify target file                                                     |
| `:Lsettings set target.input-path <file>` | specify file input (exec < file)                |
| `:Lbr`            | set breakpoint under cursor                                             |
| `:Lrun`           | run                                                                     |
| `:Lstep`          | source level single step in current thread                              |
| `:Lnext`          | source level single step over in current thread                         |
| `:Lthread step-in` | instruction level single step in current thread                         |
| `:Lthread step-over` | instruction level single step-over in current thread                    |
| `Lcontinue`       | Continue execution of all threads in the current process.               |
| `:Lfinish`        | step out of currently selected frame                                    |
| `:Lthread return <RETURN EXPRESSION>`| return immediately from currently selected frame with optional return value |
| `:Lthread select 1`| select thread 1 as default thread for subsequent commands              |
| `:Lbt all`         | thread backtrace all                                                   |
| `:Lfr v`          | show args and local vars for current frame                              |
| `:Lfr v -f x bar` | show contents of variable `bar` formatted as hex                        |
| `:Lfr v -f b bar` | same as above with binary formatting                                    |
| `:Lregister read`  | show the general purpose registers for current thread                  |
| `:Lregister read rax rsp`  | show the contents of rax, rsp                                  |
| `:Lregister write rax 123`  | write `123` into rax                                          |
| `:Ldisassemble --name main` | disassemble any functions named `main`                        |
| `:Ldisassemble --line` | disassemble current source line for current frame                  |
| `:Ldisassemble --mixed` | disassemble with mixed mode                                       |



For a complete list of commands, see [gdb to lldb map](https://lldb.llvm.org/use/map.html)


Customization
-------------

### Global options

```vim
" set python interpereter path
let g:lldb_python_interpreter_path = 'usr/bin/python'
```

```vim
" enable lldb, default is 1 {enable}, 0 {disable}
let g:lldb_enable = 1
```

```vim
" set lldb to async, default is 1 {async}, 0 {sync}
let g:lldb_async = 1
```

```vim
" set lldb console output color
:hi lldb_output ctermfg=green ctermbg=NONE guifg=green guibg=NONE
" set breakpoint color
:hi lldb_breakpoint ctermfg=white ctermbg=DarkGray guifg=white guibg=DarkGray
```


Verifying Python Support
------------------------

This plugin leverages the `LLDB` module which requires Python support.



If Vim warns that it is unable to load vim-lldb on launch, there may be mismatched versions of Python running between `LLDB` and the system Python interpreter. Versions must match exactly.
 

Verify LLDB's version of Python by launching the Python interpreter in LLDB: 

    $> lldb -b -o "script import sys; print(sys.version)"
    3.7.6 (default, ...)


If Python versions are mismatched, either recompile Python to match the exact version as LLDB or vice-versa. See [lldb caveats](https://lldb.llvm.org/resources/caveats.html) for details.

