# Forked off vim-lldb

This version of vim-lldb supports both Python2 and Python3. It is currently
under development so bugs are expected.

## Caveats

This plugin leverages the LLDB module, so requires Python support in Vim. The version of Python must also match the version of Python that LLDB is compiled against.

## TODOs

* instructions for compiling Vim/Python/LLDB to work in harmony
* add ability to set LLDB path from .vimrc in addition to env
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
