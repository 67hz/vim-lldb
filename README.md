vim-lldb
========

### LLDB debugging in Vim

This version of vim-lldb supports Python3. This was forked from the LLVM tools vim-lldb plugin built for Python2. It is currently under active development. If you see something, say something. If you are running Python2, you will have better support from the original for now. There is a @TODO task for backward-compatibility, but it is lower on the list.


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

All LLDB commands are available through `:L<lldb_command>`. Using lldb's documentation at `:Lhelp` along with `:L<tab>` tab completion for all available LLDB commands is a good place to start. Remember to prepend all commands with `:L`.
For example:

```vim
" set a target file
:Ltarget ./path/to/file
" set a breakpoint under cursor
:Lbr
" run debugger
:Lrun
" get help for continue command
:Lhelp continue
```

Example commands:


| Command           | Function                                                                    |
| ---               | ---                                                                     |
| `:Ltarget file`   | specify target file                                                     |
| `:Lbr`            | set breakpoint under cursor                                             |
| `:Lrun`           | run                                                                     |
| `:Lstep`          | source level single step in current thread                              |
| `:Lnext`          | source level single step over in current thread                         |
| `:Lsi`            | instruction level single step in current thread                         |
| `:Lni`            | instruction level single step-over in current thread                    |
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
" add custom path to lldb
let g:lldb_path="/absolute/path/to/lldb"
```

```vim
" enable lldb, default is 1 {enable}, 0 {disable}
let g:lldb_enable = 1
```

```vim
" set lldb to async, default is 1 {async}, 0 {sync}
let g:lldb_async = 1
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

* Create format for config file to define debug pane layout
    * ~~set with lldb_default_panes but no layouts available yet~~ (not yet implemented)

    ```vim
      let g:lldb_default_panes=['breakpoints', 'locals']
    ```

* Fix bug with deleted panes/buffers.
* More theming options: centralized in separate data structure(s)
  * customizable panes
  * dis view: customize number of instructions to disassemble
* Shorter commands can be ambiguous, e.g. Lb 89
* Fix arg separations for variadics, e.g. Lbreakpoint 83
* Check for vim/lldb python versions match before importing lldb.
  * currently, a SEG fault will occur if LLDB is found on the system, but the PYthon version doesn't match what Vim was compiled against
* reach feature-parity with gdb and term-debug
