""
" LLDB debugger for Vim
"
" Credits: Based largely on termdebug by Bram Moolenaar and the original vim-lldb plugin by Daniel Malea.
" Author: Aaron Hinojosa <67hz@protonmail.com>
" License: Same as Vim (see ":help license")
" Last Change: 2020 September 21 
"
" Requirements:
"  * vim must be compiled with '+terminal' support
"  * Linux or macOS
"
" TODO:
" * add help docs
" * add Windows support
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

if (exists("g:lldb_enable") && g:lldb_enable == 0 || (exists("s:lldb_term_running")) )
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


let s:script_dir = fnamemodify(resolve(expand("<sfile>:p")), ':h:h')
" Setup the python interpreter path
func! s:GetPythonScriptDir()
  return s:script_dir . "/python-vim-lldb"
endfunc


"
" UI DEFAULTS
"
" g:lldb_width = width as inverse (3 = 1/3 default)
" g:lldb_orientation = 0 - horizontal, 1 - vertical (default)
" g:lldb_rows = num rows in horizontal orientation
"

" open LLDB in 1/3 width unless defined by user
if !exists('g:lldb_width')
  let g:lldb_width = 3 
endif

" set orientation of lldb - 0 - horizontal , 1 - vertical
if !exists('g:lldb_orientation')
  let g:lldb_orientation = 0
endif



func! s:StartDebug_common()
  exe 'hi default ' . 'debugPC ctermbg=blue guibg=blue'
  call sign_define('lldb_marker', {'text': '=>', 'texthl': 'debugPC'})
  call sign_define('lldb_active', {'linehl': 'debugPC'})

  call s:InstallCommands()
  call win_gotoid(s:lldbwin)
endfunc

func! s:StartDebug_term()
  " comment out to remove logs
  "call ch_logfile('vim-lldb_logfile', 'w')

  " only 1 running instance allowed
  if (exists("s:lldb_term_running"))
    return
  endif

  let python_path = s:GetPythonPath()
  let python_script_dir = s:GetPythonScriptDir()

  let s:sourcewin = win_getid(winnr())

  " remove for single pane
  let s:debug = 1
  " use terminal as lldb output for source program
  if exists('s:debug')
    let s:lldb_comms_buf = term_start('NONE', {
          \ 'term_name': 'debugger output',
          \ 'vertical': 1,
          \ 'hidden': 0,
          \})

    let pty_out = job_info(term_getjob(s:lldb_comms_buf))['tty_out']
    let pty_in = job_info(term_getjob(s:lldb_comms_buf))['tty_in']

    if g:lldb_orientation == 1
      exe (&columns / g:lldb_width - 1) . "wincmd | "
    endif 
  endif

  "set modified


  " start LLDB interpreter in new terminal
  " the script will launch a debugger instance
  let py_script = '/lldb_commands.py'
  let cmd = python_path . ' ' . python_script_dir . py_script
  let s:lldb_native_buf = term_start(cmd, {
        \ 'term_name': 'lldb',
        \ 'vertical': 1,
        \ 'hidden': 0,
        \ 'eof_chars': 'exit',
        \})

  let lldb_options = {}
  let lldb_options['exit_cb']= function('s:EndTermDebug')
  call job_setoptions(term_getjob(s:lldb_native_buf), lldb_options)

  if s:lldb_native_buf == 0
    echohl WarningMsg python_path . ' failed to open LLDB. Try `:LInfo` for plugin info and see README for details.' | echohl None
    return
  endif

  let s:lldbwin = win_getid(winnr())
  let s:lldb_term_running = 1

  call term_setapi(s:lldb_native_buf, "Lldbapi_")

  " import custom commands into native LLDB
  let python_cmds = python_script_dir . py_script
  call s:SendCommand('command script import ' . python_cmds)

  " redirect LLDB log output to stdin of comms buff
  call s:SendCommand('set_tty_in ' . pty_in)
  call s:SendCommand('set_tty_out ' . pty_out)

  call s:StartDebug_common()
endfunc

"
" These commands should have mappings:
" breakpoints
" step-related
" watch vars
" evaluating vars - print, po
" bt
" attach
" launch
"
func s:InstallCommands()
  let save_cpo = &cpo
  set cpo&vim

  command Lldb call win_gotoid(s:lldbwin)
  command LSource call win_gotoid(s:sourcewin)
  command -nargs=? LBreak call s:ToggleBreakpoint()
  command LStep call s:SendCommand('step')
  command LNext call s:SendCommand('next')
  command LPrint call s:SendCommand('print ' . expand("<cword>"))
  command LFinish call s:SendCommand('finish -internal')
  command LRun call s:SendCommand('r')

  command LInfo call s:LldbDebugInfo()

  let &cpo = save_cpo

  call s:MapCommands()
endfunc

func s:MapCommands()
  let s:custom_map_keys = {
        \'<F1>': [#{cmd: ':Lldb', mode: 'n', withTarget: 0},
        \ #{cmd: '<C-w>:LSource', mode: 't', withTarget: 0}],
        \'<F2>': [#{cmd: ':LBreak', mode: 'n', withTarget: 0}],
        \'<F3>': [#{cmd: ':LStep', mode: 'n', withTarget: 0}],
        \'<F4>': [#{cmd: ':LNext', mode: 'n', withTarget: 0}],
        \'<F5>': [#{cmd: ':LPrint', mode: 'n', withTarget: 0}],
        \'<S-r>': [#{cmd: ':LRun', mode: 'n', withTarget: 0},
        \ #{cmd: '<C-w>:LRun', mode: 't', withTarget: 0}],
        \}
  let s:key_maps = {}

  for [keycode, mappings] in items(s:custom_map_keys)
    for cmd_dict in mappings
      let s:key_maps[keycode] = maparg(keycode, cmd_dict['mode'], 0, 1)
      exe cmd_dict['mode'] . 'noremap ' . keycode . ' ' . cmd_dict['cmd'] . '<CR>'
      endfor
  endfor

endfunc

func s:UnmapCommands()
  let idx = 0
  " normal remaps
  for [keycode, mapping] in items(s:custom_map_keys)
    for cmd_dict in mapping
      if !empty(s:key_maps[keycode])
        if exists('*mapset')
          call mapset("n", 0, s:key_maps[keycode])
        else
        " mapset() is not available on some versions of Vim
          exe cmd_dict['mode'] . 'noremap ' . s:key_maps[keycode]['lhs'] . ' ' . s:key_maps[keycode]['rhs']
        endif
      else
        " there was no mapping before the plugin so just unset lldb's binding
        exe cmd_dict['mode'] . 'noremap ' . keycode . ' <Nop>'
      endif
    endfor
  endfor

endfunc

func s:DeleteCommands()
  " TODO iterate of items(s:custom_map_keys)
endfunc

func s:EndTermDebug(job, status)
  "TODO check if buffers, values exist
  if exists('s:lldb_native_buf')
    exe 'bwipe! ' . s:lldb_native_buf
  endif
  if exists('s:lldb_comms_buf')
    exe 'bwipe! ' . s:lldb_comms_buf
  endif
  call s:DeleteCommands()
  call s:UI_RemoveBreakpoints()
  call s:UI_RemoveHighlightLine()
  call s:UnmapCommands()
  unlet! s:lldb_term_running
  unlet! s:lldbwin
  unlet! s:sourcewin
endfunc

func s:SendCommand(cmd)
  call ch_log('sending to lldb: ' . a:cmd)

  " delete any text user has input in lldb terminal before sending a command
  let current_lldb_cmd_line = trim(term_getline(s:lldb_native_buf, '.'))
  if current_lldb_cmd_line !=# '(lldb)' && len(current_lldb_cmd_line) > 0
    "exe 'termwinkey CTRL-C'
  endif
  call term_sendkeys(s:lldb_native_buf, a:cmd . "\r")
endfunc


" {'file:linenr': [id1, id2, ...], ...}
let s:breakpoints = {}

func s:breakpoints_hash_key(filename, line_nr)
  return a:filename . ':' . a:line_nr
endfunc

" set bp to line under cursor in file
func s:ToggleBreakpoint()
  " use absolute filenames
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

func s:UI_RemoveBreakpoints()
  unlet s:breakpoints
  call sign_unplace('bps')
endfunc

" add LLDB's current breakpoint locations to UI
func s:UI_SyncBreakpoints(breakpoints)
  call s:UI_RemoveBreakpoints()
  let s:breakpoints = js_decode(a:breakpoints)

  for [file_linenr, ids] in items(s:breakpoints)
    let file_linenr_arr = split(file_linenr, ':')
    call sign_place(ids[0], 'bps', 'lldb_marker', file_linenr_arr[0], {'lnum': file_linenr_arr[1]})
  endfor
endfunc


" filename:line:char -> [filename, line, col]
func s:SplitBreakpointIntoLocationList(str)
  let colon_sep = trim(substitute(a:str, '.*\sat', '', ''))
  let file_str_list = split(colon_sep, '\:')
  return file_str_list
endfunc



func s:UI_RemoveHighlightLine()
  call sign_unplace('process')
endfunc

func s:UI_HighlightLine(res)
  " remove existing highlight
  call s:UI_RemoveHighlightLine()

  let bp_list = s:SplitBreakpointIntoLocationList(a:res)
  if len(bp_list) != 3
      return
  endif

  " jump to source window if in lldb terminal
  " drop will create a new window if source window was previously deleted
  if bufnr() == s:lldb_native_buf
    call win_gotoid(s:sourcewin)
  endif

  let [filename, ln, bp_id] = bp_list
  " open file @ line #
  exe 'vert drop ' . filename . ' | :' . ln

  " keep source win synced to latest open
  let s:sourcewin = win_getid(winnr())

  call sign_place(bp_id, 'process', 'lldb_active', filename, {'lnum': ln})

  " place cursor back in lldb's terminal
  call win_gotoid(s:lldbwin)

endfunc


func! g:Lldbapi_LldbParseLogs(bufnum, args)
  let cmd = a:args[0]
  let resp = a:args[1] 
  echomsg '[PARSER] cmd: ' . cmd . ' resp: ' . resp
endfunc



" Called when lldb has new output
" parse response and update Vim instance when necessary
func! g:Lldbapi_LldbOutCb(bufnum, args)
  let cmd = a:args[0]
  echomsg 'lldb: ' . cmd . ' : ' a:args[1]
  call ch_log('lldb> : ' . cmd)

  " ignore help related
  if cmd =~? 'debugger commands'
    return
  endif
  if cmd =~? 'continue-request'
    if input('Process stopped: Continue [y/n]? ') =~? 'y'

    endif
  endif


  if cmd =~? 'breakpoint'
    "call s:UI_SyncBreakpoints(a:args[1])

  "elseif cmd =~? 'target'
    "echomsg 'Got target event'

  "
  " Process
  "
  elseif cmd =~? 'process'
    if cmd =~? 'invalid\|exited\|finished'
      call s:UI_RemoveHighlightLine()
    else
      call s:UI_HighlightLine(a:args[1])
    endif



  "
  " Stepping
  "
  elseif cmd =~? 'current file'
    call s:UI_HighlightLine(a:args[1])

  
  "
  " Default
  "
  else
    call ch_log('lldb catchall')
  endif
endfunc

func! g:Lldbapi_LldbErrCb(bufnum, args)
  echohl WarningMsg | echomsg 'lldb: ' . a:args[0] | echohl None
  call ch_log('lldb> : ' . a:args[0])
endfunc

func! g:Lldbapi_LldbErrFatalCb(bufnum, args)
  echohl ErrorMsg | echomsg 'lldb: ' . a:args[0] | echohl None
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

call s:StartDebug_term()

call s:restore_cpo()
