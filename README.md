vim-lldb
========

LLDB debugging in Vim.


Installation
------------

The recommended install procedure for any plugin is with Vim's native package manager.
See `:help packages` for details.


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
| `:Lldb`          |  Jump to lldb terminal window |
| `:LSource`          |  Jump to source window |
| `:LBreak`          | Toggle breakpoint under cursor                                |
| `:LStep`          | Step |
| `:LNext`          | Next
| `:LPrint`          | Print variable under cursor |
| `:LRun`          | Run target |
| `:LInfo`          | Display system info (useful for troubleshooting setup)         | 



Customization
-------------

```vim

" set path to lldb executable
let g:lldb_path = 'usr/local/bin/lldb'

" set orientation of lldb window, default is 1 (vertical), 0 horizontal
let g:lldb_orientation = 1

" set opening width of LLDB terminal as inverse value, default is 3 = 1/3 width
let g:lldb_width = 3

" set num rows for horizontal orientation
let g:lldb_rows = 3
```


### Troubleshooting:

Get information about the host information:

```vim
:LInfo
```

