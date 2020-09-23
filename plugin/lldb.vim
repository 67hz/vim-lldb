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
" * add tab completion for commands
" * add Windows support
" * add prompt fallback if '-terminal'
" * add GDB-like layouts for predefined UI setup (e.g., layout reg)
" * add panel for additional python interpreter if user requests 'script'
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

" set up UI defaults
" lldb term - vertical
let s:vertical = 1

func! s:StartDebug_common()
  exe 'hi default ' . 'debugPC ctermbg=blue guibg=blue'
  call sign_define('lldb_marker', {'text': '=>', 'texthl': 'debugPC'})
  call sign_define('lldb_active', {'linehl': 'debugPC'})



  call s:InstallCommands()
endfunc

func! s:StartDebug_term()
  " comment out to remove logs
  "call ch_logfile('vim-lldb_logfile', 'w')

  " only 1 running instance allowed
  if (exists("s:lldb_term_running"))
    return
  endif

  let s:sourcewin = win_getid(winnr())

  let python_path = s:GetPythonPath()
  let python_script_dir = s:GetPythonScriptDir()


  let cmd = python_path . ' ' . python_script_dir . '/lldb_runner.py'

  " lldb runner launched in new terminal
  let s:lldb_buf = term_start(cmd, {
       \ 'term_name': 'lldb_runner',
       \ 'vertical': s:vertical,
       \ 'term_finish': 'close',
       \ 'hidden': 0,
       \ 'norestore': 1,
       \ })
 
  if s:lldb_buf == 0
    echohl WarningMsg python_path . ' failed to open LLDB. Try `:LInfo` for plugin info and see README for details.' | echohl None
    return
  endif

  call job_setoptions(term_getjob(s:lldb_buf), {'exit_cb': function('s:EndTermDebug')})

  call term_setapi(s:lldb_buf, "Lldbapi_")
  set modified
  let s:lldb_term_running = 1

  " UI TODO: lldb gets left 1/3 - define sensible, overridable defaults
  if s:vertical
    exe (&columns / 3 - 1) . "wincmd | "
  endif 
  let s:lldbwin = win_getid(winnr())

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
  command LFinish call s:SendCommand('finish --internal')

  command LInfo call s:LldbDebugInfo()

  let &cpo = save_cpo

  call s:MapCommands()
endfunc

func s:MapCommands()
  let s:custom_map_keys = {
        \'<F1>': 'Lldb',
        \'<F2>': 'LBreak',
        \'<F3>': 'LStep',
        \'<F4>': 'LNext',
        \'<F5>': 'LPrint'
        \}
  let s:key_maps = {}

  for [key, mapping] in items(s:custom_map_keys)
    " REVIEW: Vim F1 help does not return in maparg. Is this a bug in maparg()
    let s:key_maps[key] = maparg(key, 'n', 0, 1)
    "echomsg string(s:key_maps[key])

    exe 'nnoremap ' . key . ' :' . mapping . '<CR>'
  endfor

  " terminal-only
  let s:custom_map_keys_terminal = {
        \'<C-l>': 'clear --internal',
        \'<C-z>': 'wipe --internal',
        \'<F1>': '<C-w>:LSource'
        \}
  let s:key_maps_terminal = {}
  for [key, mapping] in items(s:custom_map_keys_terminal)
    let s:key_maps_terminal[key] = maparg(key, 'n', 0, 1)
    "echomsg string(s:key_maps_terminal[key])
    exe 'tnoremap ' . key . ' ' . mapping . '<CR>'
  endfor

endfunc

func s:UnmapCommands()
  let idx = 0
  " normal remaps
  for [key, mapping] in items(s:custom_map_keys)
    if !empty(s:key_maps[key])
      if exists('*mapset')
        call mapset("n", 0, s:key_maps[key])
      else
      " mapset() is not available on some versions of Vim
        exe 'nnoremap ' . s:key_maps[key]['lhs'] . ' ' . s:key_maps[key]['rhs']
      endif
    else
      " there was no mapping before the plugin so just unset lldb's binding
      exe 'nnoremap ' . key . ' <Nop>'
    endif
  endfor

  " terminal remaps
  for [key, mapping] in items(s:custom_map_keys_terminal)
    if !empty(s:key_maps_terminal[key])
      if exists('*mapset')
        call mapset("n", 0, s:key_maps_terminal[key])
      else
        exe 'tnoremap ' . s:key_maps_terminal[key]['lhs'] . ' ' . s:key_maps_terminal[key]['rhs']
      endif
    else
      " there was no mapping before the plugin so just unset lldb's binding
      exe 'tnoremap ' . key . ' <Nop>'
    endif
  endfor

endfunc

func s:DeleteCommands()
  delcommand Lldb
  delcommand LSource
  delcommand LStep
  delcommand LNext
  delcommand LFinish
  delcommand LBreak
  delcommand LPrint
endfunc

func s:EndTermDebug(job, status)
  call s:UI_RemoveBreakpoints()
  call s:UI_RemoveHighlightLine()
  call s:DeleteCommands()
  unlet s:lldb_term_running

  exe 'bwipe! ' . s:lldb_buf

  unlet s:lldbwin
  unlet s:sourcewin
  call s:UnmapCommands()

endfunc

func s:SendCommand(cmd)
  call ch_log('sending to lldb: ' . a:cmd)

  " delete any text user has input in lldb terminal before sending a command
  let current_lldb_cmd_line = trim(term_getline(s:lldb_buf, '.'))
  if current_lldb_cmd_line !=# '(lldb)' && len(current_lldb_cmd_line) > 0
    call term_sendkeys(s:lldb_buf, 'wipe --internal ' . "\r")
  endif
  call term_sendkeys(s:lldb_buf, a:cmd . "\r")
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

func s:GetBreakpoints()
  call s:SendCommand('bp_sync --internal')
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

func s:GetAbsFilePathFromFrame()
  call s:SendCommand('frame_path --internal')
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
  if bufnr() == s:lldb_buf
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


" Called when lldb has new output
func! g:Lldbapi_LldbOutCb(bufnum, args)
  let resp = a:args[0]
  call ch_log('lldb> : ' . resp)

  "
  " Process
  "
  if resp =~? 'process'
    if resp =~? 'invalid\|exited\|finished'
      call s:UI_RemoveHighlightLine()
    else
      call s:GetAbsFilePathFromFrame()
    endif

  elseif resp =~? 'current file'
    call s:UI_HighlightLine(a:args[1])

  "
  " Breakpoint
  "
  elseif resp =~? 'Breakpoint' && resp !~? 'warning\|pending\|current\|process'
    if resp =~? 'updated'
      call s:UI_SyncBreakpoints(a:args[1])
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

call s:StartDebug_term()

call s:restore_cpo()
