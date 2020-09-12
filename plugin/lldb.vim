"
" LLDB debugger for Vim
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

function! s:Highlight()
  if !hlexists("lldb_output")
    :hi lldb_output ctermfg=NONE ctermbg=NONE guifg=NONE guibg=NONE 
  endif
  if !hlexists("lldb_breakpoint")
    :hi lldb_breakpoint ctermfg=NONE ctermbg=NONE guifg=NONE guibg=NONE 
  endif
  if !hlexists("lldb_pc_active")
    :hi lldb_pc_active ctermfg=White ctermbg=Blue guifg=White guibg=Blue
  endif
  if !hlexists("lldb_pc_inactive")
    :hi lldb_pc_inactive ctermfg=NONE ctermbg=LightGray guifg=NONE guibg=LightGray
  endif
  if !hlexists("lldb_changed")
    :hi lldb_changed ctermfg=DarkGreen ctermbg=White guifg=DarkGreen guibg=White
  endif
  if !hlexists("lldb_selected")
    :hi lldb_selected ctermfg=LightYellow ctermbg=DarkGray guifg=LightYellow guibg=DarkGray
  endif
endfunction

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

func! s:StartDebug_prompt()
  if s:vertical
    vertical new
  else
    new
  endif

  let s:lldbpromptwin = win_getid(winnr())
  let s:promptbuf = bufnr('')
  call prompt_setprompt(s:promptbuf, 'lldb-client> ')
  set buftype=prompt
  call prompt_setcallback(s:promptbuf, function('s:PromptCallback'))
  "call prompt_setinterrupt(s:promptbuf, function('s:PromptInterrupt'))

  if s:vertical
    exe (&columns / 3 - 1) . "wincmd | "
  endif

  let cmd = ['lldb']
  let s:lldbjob = job_start(cmd, {
        \ 'out_cb': function('s:LldbOutCallback'),
        \ })

  if job_status(s:lldbjob) != "run"
    echoerr "Failed to start lldb "
  else
    echo "running job"
    let info = job_info(s:lldbjob)
    let s:lldb_loaded = 1
    echo "Exitcode = " . info.exitval
  endif

  " mark buffer so not easy to close
  set modified
  let s:lldb_channel = job_getchannel(s:lldbjob)
endfunc

func! s:LldbOutCallback(text)
  echo a:text
  call ch_log('lldb outcallback: ' . a:text)
endfunc

func! s:PromptCallback(text)
  call ch_log('prompt callback: ' . a:text)
  call s:SendCommand(a:text)
endfunc


func! s:StartDebug_term()
  " comment out to remove logs
  call ch_logfile('vim-lldb_logfile', 'w')

  " only 1 running instance allowed
  if (exists("s:lldb_term_running"))
    return
  endif

  " lldb server
  let s:ptybuf = term_start(g:lldb_python_interpreter_path . ' ' . g:vim_lldb_pydir . '/lldb_server.py', {
       \ 'term_name': 'lldb_server',
       \ 'vertical': s:vertical,
       \ 'term_finish': 'close',
       \ 'hidden': 0,
       \ })

  let s:lldb_term_running=1

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

  command -nargs=? Lbreakpoint call s:SetBreakpoint(<q-args>)
  command LStartDebug call s:StartDebug_term()

  let &cpo = save_cpo
endfunction

" default to line under cursor in file
func s:SetBreakpoint(at)
   let at = empty(a:at) ?
         \ 'set --file ' . fnameescape(expand('%:p')) . ' --line ' . line('.') : a:at
  call s:SendCommand('breakpoint ' . at)
endfunc

func s:SendCommand(cmd)
  call ch_log('sending to lldb: ' . a:cmd)
  call term_sendkeys(s:ptybuf, a:cmd . "\r")
endfunc


" TODO: handle full list as 'breakpoint list'
func s:UI_Breakpoint(at)
  let at = a:at[0]

  let colon_sep = trim(substitute(at, '.*at', '', ''))
  " above resolves to -> 'file:line:char'

  let file_str = split(colon_sep, '\:')
  let file = file_str[0]
  let ln = file_str[1]
  "echomsg 'filename:' . file . ' at line=' . ln
  exe 'sign place 2 line=' . ln . ' name=lldb_marker file=' . file
endfunc

func! g:Tapi_LldbOutCb(bufnum, args)
  if a:args[0] =~ 'Breakpoint' && a:args[0] !~ 'WARNING'
    " update breakpoint in UI
    call s:UI_Breakpoint(a:args)
  else
    echomsg 'lldb args: ' . a:args[0]
    call ch_log('lldb> : ' . a:args[0])
  endif
endfunc

func! g:Tapi_LldbErrCb(bufnum, args)
  echomsg 'lldb error: ' . a:args[0]
  call ch_log('lldb> : ' . a:args[0])
endfunc


" Returns cword if search term is empty
function! s:CursorWord(term) 
  return empty(a:term) ? expand('<cword>') : a:term 
endfunction

" Returns cleaned cWORD if search term is empty
function! s:CursorWORD(term) 
  " Will strip all non-alphabetic characters from both sides
  return empty(a:term) ?  substitute(expand('<cWORD>'), '^\A*\(.\{-}\)\A*$', '\1', '') : a:term 
endfunction

augroup VimLLDB
  autocmd!
  au ColorScheme * call s:Highlight()
augroup END

call s:StartDebug_common()
"call s:StartDebug_prompt()


call s:restore_cpo()
