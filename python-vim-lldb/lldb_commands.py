#!/usr/bin/python

# TODO: check loading init files doesn't break anything
# See TestFrameUtils.py for get_args_as_string(frame0) and lldbutil.print_stacktrace(thread)
# See lldb-vscode/lldb-vscode.cpp
# SBHostOS: GetLLDBPath, GetLLDBPythonPath


import lldb
import shlex
import optparse
from sys import __stdout__
from re import compile, VERBOSE, search, sub
import threading

OUT_FD = None

# 7/8-bit C1 ANSI sequences
ansi_escape = compile(
    br'(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])'
)

def escape_ansi(line):
    return ansi_escape.sub(b'', bytes(line))

def escapeQuotes(res):
    res = escape_ansi(res.encode("utf-8", "replace"))
    res = str(res.decode("utf-8"))
    res = res.replace('"', '\\\"')
    res = res.replace("'", '\\\"')
    return res

def vimOutCb(method, res, data = ''):
    """ Escape sequence to trap into Vim's cb channel.
        See :help term_sendkeys for job -> vim communication """
    print('\033]51;["call","Lldbapi_Lldb{}", ["{}", "{}"]]\007'.format(method, escapeQuotes(res), data))

def vimErrCb(err):
    print('\033]51;["call","Lldbapi_LldbErrCb",["{}"]]\007'.format(escapeQuotes(err)))



#
# Define custom commands for LLDB
#

def get_tty(debugger, command, result, internal_dict):
    handle = debugger.GetOutputFileHandle()
    result.write('tty output: %s'% handle)

def set_log_tty(debugger, command, result, internal_dict):
    """ set log output tty """
    args = shlex.split(command)
    global OUT_FD
    OUT_FD = __stdout__
    if len(args) > 0:
        path = args[0].strip()
        print('path:%s'% path)
        OUT_FD = open(path, "w")

    #debugger.SetOutputFileHandle(OUT_FD, True)
    #handle = debugger.GetOutputFileHandle()
    #result.write('logging to fd: %s'% OUT_FD.name)
    #result.PutOutput(handle)

# TODO - this does not need to be a custom command, call lldb directly to avoid
# displaying in prompt

def bp_dict(debugger, command, result, internal_dict):
    """ return a breakpoint dict of form = {'filename:line_nr': [id, id, ...]} """
    target = debugger.GetSelectedTarget()
    id_dict = {}

    for bp in target.breakpoint_iter():
        for bl in bp:
            loc = bl.GetAddress().GetLineEntry()
            key = str(loc.GetFileSpec()) + ':' + str(loc.GetLine())
            if key in id_dict:
                id_dict[key].append(bp.GetID())
            else:
                id_dict[key] = [bp.GetID()]

    #print(id_dict)
    vimOutCb('OutCb', 'breakpoint updated', id_dict)

def line_at_frame(debugger, command, result, internal_dict):
    """ return the source file's line # based on a the selected frame """
    target = lldb.debugger.GetSelectedTarget()
    if target is not None:
        process = target.GetProcess()
        for thread in process:
            frame = thread.GetSelectedFrame()
            if frame is not None:
                path = frame.GetPCAddress().GetLineEntry()
                vimOutCb('OutCb','current file', path)
    else:
        vimErrCb("Unable to get a line entry for frame")




# TODO run in separate thread
# use logging callback to launch once an active thread is established
class EventListeningThread(threading.Thread):
    def run(self):
        """ main loop to listen for LLDB events """
        event = lldb.SBEvent()
        listener = lldb.debugger.GetListener()
        num_tries = 5

        while True:
            print('listening: %s'% listener)
            if listener.WaitForEvent(1, event):
                print('hello')
                ev_mask = event.GetType()
                print('type: %s', ev_mask)
            num_tries -= 1
            if num_tries == 0:
                break
        listener.Clear()
        return



""" Send logs off to Vim for parsing """
def log_cb(msg):
    # output logs for debugging only
    if OUT_FD:
        print('still out')
        OUT_FD.write(msg)

    if 0:
        log_id = compile(r'\d*?\.\d*\s?')
        heading = compile('(\w*)\:\:(\w*)')
        header = search(heading, msg)
        print('parent: ', header.group(1))
        print('sub: ', header.group(2))

        if header.group(1) == 'Target':
            if header.group(2) == 'Target':
                print('New Target')
            if header.group(2) == 'AddBreakpoint':
                print(DBG)
                DBG.HandleCommand('bp_dict')

        vimOutCb('ParseLogs', 'lldb-log', msg)






def __lldb_init_module(debugger, internal_dict):
    # initialize global setup here
    # for lldb->vim comms use vimOutCb or logging or override HandleCommand globally?
    # apropros log
    lldb.debugger.SetPrompt('(vim-lldb)')
    lldb.debugger.SetLoggingCallback(log_cb)

    global DBG
    DBG = lldb.debugger

    # (lldb) log list  - list channels/categories
    #lldb.debugger.EnableLog('lldb', ['break', 'target', 'step'])
    lldb.debugger.EnableLog('lldb', ['default'])

    lldb.debugger.HandleCommand('command script add -f lldb_commands.bp_dict bp_dict')
    print('The "bpdict" command has been installed')
    lldb.debugger.HandleCommand('command script add -f lldb_commands.line_at_frame line_at_frame')
    print('The "line_at_frame" command has been installed')
    lldb.debugger.HandleCommand('command script add -f lldb_commands.set_log_tty set_log_tty')
    print('The "set_log_tty" command has been installed')
    lldb.debugger.HandleCommand('command script add -f lldb_commands.get_tty get_tty')
    print('The "get_tty" command has been installed')




    if 0:
        eventsThread = EventListeningThread()
        eventsThread.context = debugger
        #eventsThread.setDaemon(True)
        eventsThread.start()
        eventsThread.join()




