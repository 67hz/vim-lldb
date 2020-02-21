# Forked off vim-lldb

This fork is in discovery mode.

##Tasks


* Update to support python3

* Look into term-debug and potential feature parity with gdb

* Uncover more @TODOs as I dig deeper into LLDB






# Python 2/3 support

  See `:help pyx` for more info
  If a user prefers Python 2 and want to fallback to Python 3, he needs to set

      'pyxversion' explicitly in his |.vimrc|.  E.g.: >
        if has('python')
          set pyx=2
        elseif has('python3')
          set pyx=3
        endif
