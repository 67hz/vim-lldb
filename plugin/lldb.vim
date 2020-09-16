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
let s:breakpoint_locations = {}

func s:breakpoints_hash_key(filename, line_nr)
  return a:filename . ':' . a:line_nr
endfunc

func s:breakpoints._getIDs(filename, line_nr)
  let file_ln_key = s:breakpoints_hash_key(a:filename, a:line_nr)

  if has_key(s:breakpoints, file_ln_key)
    let bps = s:breakpoints[file_ln_key]
    if (len(bps) == 1)
      " return 1st item in list
      return bps[0]
    else
      " prompt user of available ids to delete
    endif
    echomsg 'length of bp list' . len(s:breakpoints[file_ln_key])

    return bps
  endif
  return []
endfunc

" breakpoints = {filename:line_nr: [id, id, ...]
func s:breakpoints._add(filename, line_nr, bp_id)
  let file_ln_key = s:breakpoints_hash_key(a:filename, a:line_nr)
  if has_key(s:breakpoints, file_ln_key)
    " add bp id if does not exist under file:line_nr
    if index(s:breakpoints[file_ln_key], a:bp_id) == -1
      call insert(s:breakpoints[file_ln_key], a:bp_id)
    endif
  else
    " add a new entry for breakpoint id
    let s:breakpoints[file_ln_key] = [a:bp_id]
  endif
endfunc

func s:breakpoints._remove(filename, line_nr)
  let idx = s:breakpoints._getIDs(a:filename, a:line_nr)
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
  let bp_ids = s:breakpoints._getIDs(filename, line_nr)

  if len(bp_ids) > 0
    " found matching breakpoint so toggle off

    if (len(bp_ids)) == 1

      call s:SendCommand('breakpoint delete ' . bp_ids[0])
    else
    " TODO if deleting with more than one bp location under cursor, prompt user to
    " select id to delete: could be a quickfix window or prompt?
    endif
  else
    " no match so toggle on
    call s:SendCommand('breakpoint ' . arg_string)
  endif
endfunc

func s:UI_AddBreakpoint(res)
  let [filename, line_nr, bp_id] = s:GetBreakpointAsList(a:res)
  call s:breakpoints._add(filename, line_nr, bp_id)
  exe 'sign place 2 line=' . line_nr . ' name=lldb_marker file=' . filename
endfunc

func s:UI_SyncBreakpoints(res)
  call s:SendCommand('bp_ids --internal')
endfunc

func s:UI_UpdateBreakpoint(res)
  let bp_ids = trim(substitute(a:res[0], '.*\(\[.*\)', '\1', ''))
  "let bp_ids = trim(substitute(a:str[0], '.*Breakpoint\s\([0-9]\)\(.*\)', '\1', ''))
  echomsg 'remove bp placeholder: ' . bp_ids
endfunc


func s:UI_HighlightLine(res)
  " remove existing highlight

  let [filename, ln, bp_id] = s:GetBreakpointAsList(a:res)

  " open file
  " TODO get fullname from filename, vsp or split based on defaults
  " open files if not in buffer?
  exe 'drop ' . filename . ' '
  exe 'sign place 2 line=' . ln . ' name=lldb_active file=' . filename
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
  elseif a:args[0] =~? 'Breakpoint' && a:args[0] !~? 'warning\|pending\|current'
    if a:args[0] =~? 'all-ids'
      call s:UI_UpdateBreakpoint(a:args)

    elseif a:args[0] =~? 'deleted'
      call s:UI_SyncBreakpoints(a:args)
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
  echohl WarningMsg | echo 'lldb error: ' . a:args[0] | echohl None
  call ch_log('lldb> : ' . a:args[0])
endfunc

func! g:Tapi_LldbErrFatalCb(bufnum, args)
  echohl WarningMsg | echo 'lldb error: ' . a:args[0] | echohl None
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

call s:restore_cpo()
