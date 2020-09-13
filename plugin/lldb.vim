"
" LLDB debugger for Vim
"
" TODO:
" 
" * add breakpoints_by_name {} to allow deleting by name, use as cross-ref
" from s:breakpoints {}
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
  sign define lldb_marker text=>> texthl=Search
  sign define lldb_active linehl=Search
  sign define lldb_inactive linehl=None
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
  "echomsg 'BufRead'
endfunc


func! s:StartDebug_term()
  " comment out to remove logs
  call ch_logfile('vim-lldb_logfile', 'w')

  " only 1 running instance allowed
  if (exists("s:lldb_term_running"))
    return
  endif

  " lldb server launched in new terminal
  let s:ptybuf = term_start(g:lldb_python_interpreter_path . ' ' . g:vim_lldb_pydir . '/lldb_server.py', {
       \ 'term_name': 'lldb_server',
       \ 'vertical': s:vertical,
       \ 'term_finish': 'close',
       \ 'hidden': 0,
       \ })

  let s:lldb_term_running = 1

  " UI TODO: lldb gets left 1/3 - define sensible, overridable defaults
  if s:vertical
    exe (&columns / 3 - 1) . "wincmd | "
  endif

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
function! s:InstallCommands()
  let save_cpo = &cpo
  set cpo&vim

  " TODO add breakpoint with args
  "command -nargs=? Lbreakpoint call s:Breakpoint(<q-args>)
  command -nargs=? Lbreakpoint call s:ToggleBreakpoint()
  command LStartDebug call s:StartDebug_term()

  let &cpo = save_cpo

  nnoremap <C-l> :Lbreakpoint<CR>
endfunction

func s:SendCommand(cmd)
  call ch_log('sending to lldb: ' . a:cmd)
  " TODO call clear line before cmd in case user typed input into prompt
  " without executing
  call term_sendkeys(s:ptybuf, a:cmd . "\r")
endfunc

" returns [filename, line_nr, breakpoint id] from lldb output string
func s:GetBreakpointAsList(str)
  let bp_id = trim(substitute(a:str[0], '.*Breakpoint\s\([0-9]\)\(.*\)', '\1', ''))
  echomsg 'bp_id: ' . bp_id
  let colon_sep = trim(substitute(a:str[0], '.*at', '', ''))
  let file_str = split(colon_sep, '\:')
  echo 'file: ' . file_str[0] . ' ln: ' . file_str[1] . ' bp_id: ' . bp_id
  return [file_str[0], file_str[1], bp_id]
endfunc

" TODO decide on relative or abs paths, add breakpoints_by_name {}
let s:breakpoints = {}

func s:breakpoints._exists(filename, line_nr)
  if has_key(s:breakpoints, a:filename)
    return index(s:breakpoints[a:filename], ''. a:line_nr)
  endif
  return -1
endfunc

func s:breakpoints._add(filename, line_nr, bp_id)
  if has_key(s:breakpoints, a:filename)
    " add bp if does not exist under file
    if index(s:breakpoints[a:filename], a:line_nr) == -1
      call insert(s:breakpoints[a:filename], a:line_nr)
    endif
  else
    " add a new file entry for breakpoint
    let s:breakpoints[a:filename] = [a:line_nr]
  endif
endfunc

func s:breakpoints._remove(filename, line_nr)
  let idx = s:breakpoints._exists(a:filename, a:line_nr)
  call remove(s:breakpoints[a:filename], idx)
endfunc

" set bp to line under cursor in file
func s:ToggleBreakpoint()
  " abs
  "let filename = fnameescape(expand('%:p')) 
  " relative - tail only
  let filename = fnameescape(expand('%:t'))
  let line_nr = line('.')
  let arg_string = 'set --file ' . filename . ' --line ' . line_nr

  if s:breakpoints._exists(filename, line_nr) >= 0
    " if deleting with more than one bp location at cursor, prompt user to
    " select id to delete
    " TODO send command to terminal instead of direct
    call s:breakpoints._remove(filename, line_nr)
  else
    call s:SendCommand('breakpoint ' . arg_string)
  endif
endfunc

" TODO: handle full list as 'breakpoint list'
func s:UI_AddBreakpoint(res)
  let [filename, line_nr, bp_id] = s:GetBreakpointAsList(a:res)
  call s:breakpoints._add(filename, line_nr, bp_id)
  exe 'sign place 2 line=' . line_nr . ' name=lldb_marker file=' . filename
endfunc

func s:UI_RemoveBreakpoint(res)
  echomsg 'remove bp placeholder'
endfunc


func s:UI_HighlightLine(res)
  " remove existing highlight

  let [file, ln, bp_id] = s:GetBreakpointAsList(a:res)

  " drop to open file
  exe 'sign place 2 line=' . ln . ' name=lldb_active file=' . file
endfunc


func! g:Tapi_LldbOutCb(bufnum, args)
  echomsg 'lldb args: ' . a:args[0]
  call ch_log('lldb> : ' . a:args[0])

  "
  " Process
  "
  if a:args[0] =~? 'Process' && a:args[0] !~? 'invalid'
    call s:UI_HighlightLine(a:args)

  "
  " Breakpoint
  "
  elseif a:args[0] =~? 'Breakpoint' && a:args[0] !~? 'warning'
    if a:args[0] =~? 'deleted'
      call s:UI_RemoveBreakpoint(a:args)
    else
      " update breakpoint in UI
      call s:UI_AddBreakpoint(a:args)
    endif
  
  "
  " Default
  "
  else
    call ch_log('lldb catchall')
  endif
endfunc

func! g:Tapi_LldbErrCb(bufnum, args)
  echomsg 'lldb error: ' . a:args[0]
  call ch_log('lldb> : ' . a:args[0])
endfunc

func! g:DebugBreakpoints()
  for key in keys(s:breakpoints)
    if key !~ '^_'
      echo 'key:' . key . '<'
      for bp in s:breakpoints[key]
        echo 'bp@line#: ' . bp
      endfor
    endif
  endfor
endfunc

call s:StartDebug_common()

call s:restore_cpo()
