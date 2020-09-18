""
" LLDB debugger for Vim
"
" Author: Aaron Hinojosa <67hz@protonmail.com>
" License: Same as Vim (see ":help license")
"
" Notes:
"  * vim must be compiled with '+terminal' support
"  * Linux and macOS are supported
"
" TODO:
" * add help docs
" * add tab completion for commands
" * add windows support
" * add prompt fallback if '-terminal'
" * add GDB-like layouts for predefined UI setup (e.g., layout reg)
"
""

let s:keepcpo = &cpo
set cpo&vim

func! s:restore_cpo()
  let &cpo = s:keepcpo
  unlet s:keepcpo
endfunc


if(v:version < 801)
  call confirm('ERROR: lldb requires vim > v8.1.0. lldb debugging is disabled.')
  call s:restore_cpo()
  finish
elseif(!has('terminal'))
  call confirm('ERROR: lldb requires terminal support in vim')
  call s:restore_cpo()
  finish
endif 

func! s:GetLLDBPath()
  if !exists('g:lldb_path')
    let g:lldb_path = 'lldb'
  endif
  return g:lldb_path
endfunc

func! s:GetPythonPathFromLLDB()
  let lldb_exec = s:GetLLDBPath()
  :silent let path = systemlist(lldb_exec . ' -b -o "script import sys; print(sys.executable)"')
  if len(path) < 1
    return ''
  elseif  path[1] !~? 'python'
      return ''
  else
    " return python path from lldb's output
    return path[1]
  endif
endfunc

func! s:GetPythonPath()
  if !exists("g:lldb_python_interpreter_path")
    let lldb_python_path = s:GetPythonPathFromLLDB()
    if lldb_python_path == ''
      " try default Python interpreter if lldb shell fails to return path
      let g:lldb_python_interpreter_path = 'python'
    else
      " got a valid value back from lldb's output
      let g:lldb_python_interpreter_path = lldb_python_path
    endif

    return g:lldb_python_interpreter_path
  else
    " or use the user's value from .vimrc if it exists
    return g:lldb_python_interpreter_path
  endif
endfun

if (exists("g:lldb_enable") && g:lldb_enable == 0 || (exists("s:lldb_loaded")) )
  call s:restore_cpo()
  finish
endif

let s:script_dir = fnamemodify(resolve(expand("<sfile>:p")), ':h:h')
" Setup the python interpreter path
func! s:GetPythonScriptDir()
  return s:script_dir . "/python-vim-lldb"
endfunc

" set up UI defaults
" lldb term - vertical
let s:vertical = 1

func! s:StartDebug_common()
  exe 'hi default ' . 'debugPC ctermbg=blue guibg=blue'
  call sign_define('lldb_marker', {'text': '=>', 'texthl': 'debugPC'})
  call sign_define('lldb_active', {'linehl': 'debugPC'})

  call s:InstallCommands()

  " remove before Prod - defer launch until user engages
  " auto start for debugging only
  call s:StartDebug_term()

  augroup TermDebug
    au BufRead * call s:BufRead()
endfunc

" TODO: handle updates common to all lldb responses
" may not be needed if handling updates on an individual basis
func s:BufRead()
endfunc


func! s:StartDebug_term()
  " comment out to remove logs
  "call ch_logfile('vim-lldb_logfile', 'w')

  let python_path = s:GetPythonPath()
  let python_script_dir = s:GetPythonScriptDir()

  " only 1 running instance allowed
  if (exists("s:lldb_term_running"))
    return
  endif
  let cmd = python_path . ' ' . python_script_dir . '/lldb_server.py'

  " lldb server launched in new terminal
  let s:ptybuf = term_start(cmd, {
       \ 'term_name': 'lldb_server',
       \ 'vertical': s:vertical,
       \ 'term_finish': 'close',
       \ 'hidden': 0,
       \ })
 
  if s:ptybuf == 0
    echohl WarningMsg python_path . ' failed to open LLDB. Try `:LInfo` for plugin info and see README for details.' | echohl None
    return
  endif

  call term_setapi(s:ptybuf, "Lldbapi_")
  set modified
  let s:lldb_term_running = 1

  " UI TODO: lldb gets left 1/3 - define sensible, overridable defaults
  if s:vertical
    exe (&columns / 3 - 1) . "wincmd | "
  endif 
  let s:lldbwin = win_getid(winnr())
endfunc

"
" These commands should have mappings:
" breakpoints
" step-related
" watch vars
" bt
" attach
" launch
"
func s:InstallCommands()
  let save_cpo = &cpo
  set cpo&vim

  command -nargs=? LBreak call s:ToggleBreakpoint()
  command Lldb call win_gotoid(s:lldbwin)
  command LStep call s:SendCommand('step')
  command LNext call s:SendCommand('next')
  command LFinish call s:SendCommand('finish --internal')

  command LInfo call s:LldbDebugInfo()

  let &cpo = save_cpo

  call s:MapCommands()
endfunc

func s:MapCommands()
  nnoremap <C-l> :LBreak<CR>

  " terminal-only
  tnoremap <C-l> clear --internal<CR>
  "tnoremap <C-c> wipe --internal<CR>
endfunc

func s:DeleteCommands()
  delcommand Lldb
  delcommand LStep
  delcommand LNext
  delcommand LFinish
  delcommand LBreak
endfunc

func s:SendCommand(cmd)
  call ch_log('sending to lldb: ' . a:cmd)
  " TODO clear line before cmd in case user typed input into prompt
  " without executing
  " check if term_getline contains user text and thenn
  " call term_sendkeys(s:ptybuf, 'wipe --internal ' . "\r")
  call term_sendkeys(s:ptybuf, a:cmd . "\r")
endfunc


" {'file:linenr': [id1, id2, ...], ...}
let s:breakpoints = {}

func s:breakpoints_hash_key(filename, line_nr)
  return a:filename . ':' . a:line_nr
endfunc

" set bp to line under cursor in file
func s:ToggleBreakpoint()
  " absoluter filenames
  let filename = fnameescape(expand('%:p')) 

  let line_nr = line('.')
  let arg_string = 'set --file ' . filename . ' --line ' . line_nr
  let hash_key = s:breakpoints_hash_key(filename, line_nr)

  if (empty(s:breakpoints))
    " add breakpoint if none exist
    call s:SendCommand('breakpoint ' . arg_string)

  elseif has_key(s:breakpoints, hash_key)
    " if bp exists at location toggle off (delete)

    if len(s:breakpoints[hash_key]) > 1
      let id = inputlist(['Multiple breakpoints at cursor. Choose id to delete:', join(s:breakpoints[hash_key])])
      if id < 1
        " user cancelled delete so do nothing
        return
      endif
    else
      " only 1 id at location under cursor so set id
      let id = s:breakpoints[hash_key][0]
    endif
    " now delete
    call s:SendCommand('breakpoint delete ' . id)
  else

    " no bp under cursor so add breakpoint 
    call s:SendCommand('breakpoint ' . arg_string)
  endif
endfunc

func s:GetBreakpoints()
  call s:SendCommand('bp_sync --internal')
endfunc

func s:SyncBreakpoints(breakpoints)
  unlet s:breakpoints
  let s:breakpoints = js_decode(a:breakpoints)
  call sign_unplace('bps')

  for [file_linenr, ids] in items(s:breakpoints)
    let file_linenr_arr = split(file_linenr, ':')
    call sign_place(ids[0], 'bps', 'lldb_marker', file_linenr_arr[0], {'lnum': file_linenr_arr[1]})
  endfor
endfunc


" str as filename:line:char
func s:GetBreakpointAsList(str)
  let colon_sep = trim(substitute(a:str, '.*at', '', ''))
  let file_str = split(colon_sep, '\:')
  return [file_str[0], file_str[1], file_str[2]]
endfunc

func s:GetAbsFilePathFromFrame()
  call s:SendCommand('frame_path --internal')
endfunc

func s:UI_HighlightLine(res)
  " remove existing highlight
  let [filename, ln, bp_id] = s:GetBreakpointAsList(a:res)
  call sign_unplace('process')
  " open file
  " TODO vsp or split based on defaults
  " open files if not in buffer? make an option
  exe 'drop ' . filename . ' '

  call sign_place(bp_id, 'process', 'lldb_active', filename, {'lnum': ln})

  " place cursor back in lldb's terminal
  call win_gotoid(s:lldbwin)

endfunc


func! g:Lldbapi_LldbOutCb(bufnum, args)
  let resp = a:args[0]
  call ch_log('lldb> : ' . resp)

  "
  " Process
  "
  if resp =~? 'process' && resp !~? 'invalid\|exited\|finished'
    call s:GetAbsFilePathFromFrame()

  elseif resp =~? 'current file'
    call s:UI_HighlightLine(a:args[1])

  "
  " Breakpoint
  "
  elseif resp =~? 'Breakpoint' && resp !~? 'warning\|pending\|current\|process'
    if resp =~? 'updated'
      call s:SyncBreakpoints(a:args[1])
    else
      call s:GetBreakpoints()
    endif
  
  "
  " Default
  "
  else
    call ch_log('lldb catchall')
  endif
endfunc

func! g:Lldbapi_LldbErrCb(bufnum, args)
  echohl WarningMsg | echo 'lldb: ' . a:args[0] | echohl None
  call ch_log('lldb> : ' . a:args[0])
endfunc

func! g:Lldbapi_LldbErrFatalCb(bufnum, args)
  echohl WarningMsg | echo 'lldb: ' . a:args[0] | echohl None
  call ch_log('lldb> : ' . a:args[0])
  unlet! s:lldb_term_running
  call s:DeleteCommands()
endfunc

func! s:LldbDebugInfo()
  let dbg_dict = {}
  let dbg_dict["python path"] = s:GetPythonPath()
  let dbg_dict["lldb executable path"] = s:GetLLDBPath()
  echomsg 'LLDB Debug:'
  echomsg string(dbg_dict)
endfunc

func! g:DebugBreakpoints()
  for key in keys(s:breakpoints)
    if key !~ '^_'
      echo 'key:' . key
      for bp in s:breakpoints[key]
        echo 'bp@id#: ' . bp
      endfor
    endif
  endfor
endfunc

call s:StartDebug_common()

call s:restore_cpo()
