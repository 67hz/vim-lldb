"
" LLDB debugger for Vim
"
" TODO:
" 
" see built-in functions for user lists, complete_add
" getbufinfo, getchangelist
"

let s:keepcpo = &cpo
set cpo&vim

function! s:restore_cpo()
  let &cpo = s:keepcpo
  unlet s:keepcpo
endfunction


if(v:version < 801)
  call confirm('ERROR: lldb requires vim > v8.1.0. lldb debugging is disabled.')
  call s:restore_cpo()
  finish
endif 

if (!exists("g:lldb_python_interpreter_path"))
  let g:lldb_python_interpreter_path = 'python'
endif

if (exists("g:lldb_enable") && g:lldb_enable == 0 || (exists("s:lldb_loaded")) )
  call s:restore_cpo()
  finish
endif

" Setup the python interpreter path
let s:script_dir = resolve(expand("<sfile>:p:h"))
function! s:FindPythonScriptDir()
  let base_dir = fnamemodify(s:script_dir, ':h')
  return base_dir . "/python-vim-lldb"
endfunction

let g:vim_lldb_pydir = s:FindPythonScriptDir()

" set up UI defaults
" lldb term - vertical
let s:vertical = 1

func! s:StartDebug_common()
  call sign_define('lldb_marker', {'text': '=>', 'texthl': 'Search'})
  call sign_define('lldb_active', {'linehl': 'Search'})
  call sign_define('lldb_inactive', {'linehl': 'None'})

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
  call ch_logfile('vim-lldb_logfile', 'w')

  " only 1 running instance allowed
  if (exists("s:lldb_term_running"))
    return
  endif

  " lldb server launched in new terminal
  " TODO error check if launch fails?
  let s:ptybuf = term_start(g:lldb_python_interpreter_path . ' ' . g:vim_lldb_pydir . '/lldb_server.py', {
       \ 'term_name': 'lldb_server',
       \ 'vertical': s:vertical,
       \ 'term_finish': 'close',
       \ 'hidden': 0,
       \ })

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
"
" maybe:
" attach
" launch
"
func s:InstallCommands()
  let save_cpo = &cpo
  set cpo&vim

  " TODO add breakpoint with args
  "command -nargs=? Lbreakpoint call s:Breakpoint(<q-args>)
  command -nargs=? Break call s:ToggleBreakpoint()
  command Lldb call s:StartDebug_term()
  command Lstep call s:SendCommand('step')
  command Lnext call s:SendCommand('next')

  let &cpo = save_cpo

  nnoremap <C-l> :Break<CR>
endfunc

func s:DeleteCommands()
  delcommand Lldb
  delcommand Break
endfunc

func s:SendCommand(cmd)
  call ch_log('sending to lldb: ' . a:cmd)
  " TODO call clear line before cmd in case user typed input into prompt
  " without executing
  call term_sendkeys(s:ptybuf, a:cmd . "\r")
endfunc


" {'file:linenr': [id1, id2, ...], ...}
let s:breakpoints = {}

func s:breakpoints_hash_key(filename, line_nr)
  return a:filename . ':' . a:line_nr
endfunc

" set bp to line under cursor in file
func s:ToggleBreakpoint()
  " abs
  let filename = fnameescape(expand('%:p')) 
  " relative - tail only
  "let filename = fnameescape(expand('%:t'))
  let line_nr = line('.')
  let arg_string = 'set --file ' . filename . ' --line ' . line_nr
  let hash_key = s:breakpoints_hash_key(filename, line_nr)

  if (empty(s:breakpoints))
    " add breakpoint if none exist
    call s:SendCommand('breakpoint ' . arg_string)

  elseif has_key(s:breakpoints, hash_key)
    " if bp exists at location toggle off
    if len(s:breakpoints[hash_key]) > 1
      let id = inputlist(['Multiple breakpoints at cursor. Choose id to delete:', join(s:breakpoints[hash_key])])
      if id < 1
        " user cancelled delete so do nothing
        return
      endif
    else
      " only 1 id at location under cursor so set id to this
      let id = s:breakpoints[hash_key][0]
    endif
      call s:SendCommand('breakpoint delete ' . id)
  else
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


func s:GetBreakpointAsList(str)
  let bp_id = trim(substitute(a:str, '.*Breakpoint\s\([0-9]\)\(.*\)', '\1', ''))
  let colon_sep = trim(substitute(a:str, '.*at', '', ''))
  let file_str = split(colon_sep, '\:')
  return [file_str[0], file_str[1], bp_id]
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


func! g:Tapi_LldbOutCb(bufnum, args)
  let resp = a:args[0]
  call ch_log('lldb> : ' . resp)

  "
  " Process
  "
  if resp =~? 'process' && resp !~? 'invalid\|exited\|finished\|breakpoint'
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

func! g:Tapi_LldbErrCb(bufnum, args)
  echohl WarningMsg | echo 'lldb: ' . a:args[0] | echohl None
  call ch_log('lldb> : ' . a:args[0])
endfunc

func! g:Tapi_LldbErrFatalCb(bufnum, args)
  echohl WarningMsg | echo 'lldb: ' . a:args[0] | echohl None
  call ch_log('lldb> : ' . a:args[0])
  unlet! s:lldb_term_running
  call s:DeleteCommands()
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

func! s:TestSuite()
    call s:SendCommand('file par')
    call s:SendCommand('b main')
    call s:SendCommand('breakpoint set --file parallel_array.c --line 23')
    call s:SendCommand('breakpoint set --file parallel_array.c --line 24')
    call s:SendCommand('breakpoint delete 2')
endfunc

"call s:TestSuite()
call s:restore_cpo()
