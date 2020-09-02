"
" LLDB debugger for Vim
"

let s:keepcpo = &cpo
set cpo&vim

function! s:restore_cpo()
  let &cpo = s:keepcpo
  unlet s:keepcpo
endfunction

if !has('pythonx')
  call confirm('ERROR: This Vim installation does not have python support. lldb debugging is disabled.')
  call s:restore_cpo()
  finish
elseif (has('python3'))
  " prefer Python 3 over 2
  let s:lldb_python_version = 3
elseif (has('python'))
  let s:lldb_python_version = ""
endif

if(v:version < 801)
  call confirm('ERROR: lldb requires vim > v8.1.0. lldb debugging is disabled.')
  call s:restore_cpo()
  finish
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
    exe (&columns / 2 - 1) . "wincmd | "
  endif

  "let cmd = ['/bin/sh', ' python /home/darkbox/.vim/pack/mine/opt/vim-lldb/python-vim-lldb/lldb_client.py']
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
  let s:ptybuf = term_start('python ' . g:vim_lldb_pydir . '/lldb_server.py', {
       \ 'term_name': 'lldb_server',
       \ 'vertical': s:vertical,
       \ 'term_finish': 'close',
       \ 'hidden': 0,
       \ })

  let s:lldb_term_running=1
  let s:lldbwin = win_getid(winnr())

endfunc

function! s:InstallCommands()
  "command -nargs=0 Lldb win_gotoid(s:lldbwin)
  "echo 'win: ' . s:lldbwin

  command -nargs=? Lbreakpoint call s:SetBreakpoint(<q-args>)
  command -nargs=0 LStartDebug call s:StartDebug_term()

endfunction

" default to line under cursor in file
func s:SetBreakpoint(at)
   let at = empty(a:at) ?
         \ 'set --file ' . fnameescape(expand('%:p')) . ' --line ' . line('.') : a:at
  call s:SendCommand('breakpoint ' . at . "\r")
endfunc

func s:SendCommand(cmd)
  call ch_log('sending to lldb: ' . a:cmd)
  call term_sendkeys(s:ptybuf, a:cmd . "\r")
endfunc


func! g:Tapi_Test(args, msg)
  echo 'Tapi_Test' . a:args[0]  . ' ->1: ' . a:args[1] .  ' msg: ' . a:msg[0]
endfunc

func! g:Tapi_Error(args, msg)
  echo 'vim-lldb: ' . a:msg[0]
endfunc

func! g:Tapi_Breakpoint(args, msg)
  echo 'Tapi_Breakpoint'
  call ch_log('Tapi_Breakpoint: ' . a:args[0] . a:msg[0])
endfunc

function! g:InitLldbPlugin()

  " Key-Bindings
  " FIXME: choose sensible keybindings for:
  " - process: start, interrupt, continue, continue-to-cursor
  " - step: instruction, in, over, out
  "
  "if has('gui_macvim')
    " Apple-B toggles breakpoint on cursor
 "   map <D-B>     :Lbreakpoint<CR>
 " endif

  "
  " Register :L<Command>
  " The LLDB CommandInterpreter provides tab-completion in Vim's command mode.
  " FIXME: this list of commands, at least partially should be auto-generated
  "
  "
  " Window show/hide commands
  command -complete=custom,s:CompleteWindow -nargs=1 Lhide               pyx ctrl.doHide('<args>')
  command -complete=custom,s:CompleteWindow -nargs=0 Lshow               pyx ctrl.doShow('<args>')
 
  " Launching convenience commands (no autocompletion)
  command -nargs=* Lstart                                                pyx ctrl.doLaunch(True,  '<args>')
  command -nargs=* Lrun                                                  pyx ctrl.doLaunch(False, '<args>')
  command -nargs=1 Lattach                                               pyx ctrl.doAttach('<args>')
  command -nargs=0 Ldetach                                               pyx ctrl.doDetach()

  " Regexp-commands: because vim's command mode does not support '_' or '-'
  " characters in command names, we omit them when creating the :L<cmd>
  " equivalents.
  command -complete=custom,s:CompleteCommand -nargs=* Lregexpattach      pyx ctrl.doCommand('_regexp-attach', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lregexpbreak       pyx ctrl.doCommand('_regexp-break', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lregexpbt          pyx ctrl.doCommand('_regexp-bt', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lregexpdown        pyx ctrl.doCommand('_regexp-down', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lregexptbreak      pyx ctrl.doCommand('_regexp-tbreak', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lregexpdisplay     pyx ctrl.doCommand('_regexp-display', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lregexpundisplay   pyx ctrl.doCommand('_regexp-undisplay', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lregexpup          pyx ctrl.doCommand('_regexp-up', '<args>')

  command -complete=custom,s:CompleteCommand -nargs=* Lapropos           pyx ctrl.doCommand('apropos', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lbacktrace         pyx ctrl.doCommand('bt', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lbreakpoint        pyx ctrl.doBreakpoint('<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lcommand           pyx ctrl.doCommand('command', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Ldisassemble       pyx ctrl.doCommand('disassemble', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lexpression        pyx ctrl.doCommand('expression', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lhelp              pyx ctrl.doCommand('help', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Llog               pyx ctrl.doCommand('log', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lplatform          pyx ctrl.doCommand('platform','<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lplugin            pyx ctrl.doCommand('plugin', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lprocess           pyx ctrl.doProcess('<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lregister          pyx ctrl.doCommand('register', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lscript            pyx ctrl.doCommand('script', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lsettings          pyx ctrl.doCommand('settings','<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lsource            pyx ctrl.doCommand('source', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Ltype              pyx ctrl.doCommand('type', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lversion           pyx ctrl.doCommand('version', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=* Lwatchpoint        pyx ctrl.doCommand('watchpoint', '<args>')
 
  " Convenience (shortcut) LLDB commands
  command -complete=custom,s:CompleteCommand -nargs=* Lprint             pyx ctrl.doCommand('print', vim.eval("s:CursorWord('<args>')"))
  command -complete=custom,s:CompleteCommand -nargs=* Lpo                pyx ctrl.doCommand('po', vim.eval("s:CursorWord('<args>')"))
  command -complete=custom,s:CompleteCommand -nargs=* LpO                pyx ctrl.doCommand('po', vim.eval("s:CursorWORD('<args>')"))
  command -complete=custom,s:CompleteCommand -nargs=* Lbt                pyx ctrl.doCommand('bt', '<args>')

  " Frame/Thread-Selection (commands that also do an Uupdate but do not
  " generate events in LLDB)
  command -complete=custom,s:CompleteCommand -nargs=* Lframe             pyx ctrl.doSelect('frame', '<args>')
  command -complete=custom,s:CompleteCommand -nargs=? Lup                pyx ctrl.doCommand('up', '<args>',     print_on_success=False, goto_file=True)
  command -complete=custom,s:CompleteCommand -nargs=? Ldown              pyx ctrl.doCommand('down', '<args>', print_on_success=False, goto_file=True)
  command -complete=custom,s:CompleteCommand -nargs=* Lthread            pyx ctrl.doSelect('thread', '<args>')

  command -complete=custom,s:CompleteCommand -nargs=* Ltarget            pyx ctrl.doTarget('<args>')

  " Continue
  command -complete=custom,s:CompleteCommand -nargs=* Lcontinue          pyx ctrl.doContinue()

  " Thread-Stepping (no autocompletion)
  command -nargs=0 Lstepinst                                             pyx ctrl.doStep(StepType.INSTRUCTION)
  command -nargs=0 Lstepinstover                                         pyx ctrl.doStep(StepType.INSTRUCTION_OVER)
  command -nargs=0 Lstepin                                               pyx ctrl.doStep(StepType.INTO)
  command -nargs=0 Lstep                                                 pyx ctrl.doStep(StepType.INTO)
  command -nargs=0 Lnext                                                 pyx ctrl.doStep(StepType.OVER)
  command -nargs=0 Lfinish                                               pyx ctrl.doStep(StepType.OUT)


  " Bind/Unbind
  command -bar -bang Lunbind                call g:UnbindCursorFromLLDB()
  command -bar -bang Lbind                call g:BindCursorToLLDB()

  call s:ServiceLLDBEventQueue()
endfunction


function! s:ServiceLLDBEventQueue()
  " hack: service the LLDB event-queue when the cursor moves
  " FIXME: some threaded solution would be better...but it
  "        would have to be designed carefully because Vim's APIs are non threadsafe;
  "        use of the vim module **MUST** be restricted to the main thread.
  command -nargs=0 Lrefresh pyx ctrl.doRefresh()
  call g:BindCursorToLLDB()
endfunction


function! g:BindCursorToLLDB()
  augroup bindtocursor
    autocmd!
    autocmd CursorMoved * :Lrefresh
    autocmd CursorHold  * :Lrefresh
    autocmd VimLeavePre * pyx ctrl.doExit()
  augroup end
endfunction


function! g:UnbindCursorFromLLDB()
  augroup bindtocursor
    autocmd!
  augroup end
  echo "vim-LLDB: unbound cursor"
endfunction


function! s:CompleteCommand(A, L, P)
pyx << EOF
a = vim.eval("a:A")
l = vim.eval("a:L")
p = vim.eval("a:P")
returnCompleteCommand(a, l, p)
EOF
endfunction

function! s:CompleteWindow(A, L, P)
pyx << EOF
a = vim.eval("a:A")
l = vim.eval("a:L")
p = vim.eval("a:P")
returnCompleteWindow(a, l, p)
EOF
endfunction

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

call s:InstallCommands()
call s:StartDebug_term()
"call s:StartDebug_prompt()


call s:restore_cpo()
