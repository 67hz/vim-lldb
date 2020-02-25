# vim-lldb

## LLDB debugging in Vim

This version of vim-lldb supports both Python2 and Python3. This was forked from LLVM tools which only supports Python2. It is currently under development so there will be bugs. If you see something, say something.


## Caveats

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


@TODO add instructions for fixing mismatched versions

If versions are mismatched, either recompile Vim to match the same version as LLDB or vice-versa.

If a custom version of LLDB is compiled to match and it is not the same as the system default, link the matching `LLDB` to vim.
To set a custom path for `LLDB`, add the following to `vimrc`:

      let g:lldb_path="/path/to/lldb"

## TODOs

* better instructions for compiling Vim/Python/LLDB to work in harmony
* better containment of key-binding
  * this will allow the plugin to "clean up" after itself and roll-back in the case that the LLDB module fails to load
* Look into term-debug and potential feature parity with gdb


### Python 2/3 support

  See `:help pyx` for more info


  If a user prefers Python 2 and wants to fallback to Python 3, he needs to set `pyxversion` explicitly in his `.vimrc`

    E.g.: >
          if has('python')
            set pyx=2
          elseif has('python3')
            set pyx=3
          endif
