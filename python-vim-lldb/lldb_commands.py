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
from threading import Thread


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

def vimOutCb(res, data = ''):
    """ Escape sequence to trap into Vim's cb channel.
        See :help term_sendkeys for job -> vim communication """
    print('\033]51;["call","Lldbapi_LldbOutCb", ["{}", "{}"]]\007'.format(escapeQuotes(res), data))

def vimErrCb(err):
    print('\033]51;["call","Lldbapi_LldbErrCb",["{}"]]\007'.format(escapeQuotes(err)))

def get_tty(debugger, command, result, internal_dict):
    handle = debugger.GetOutputFileHandle()
    result.write('tty output: %s'% handle)

def set_tty(debugger, command, result, internal_dict):
    args = shlex.split(command)
    if len(args) > 0:
        path = args[0].strip()
        print('path:%s'% path)
        OUT_FD = open(path, "w")

    res = lldb.SBCommandReturnObject()

    debugger.SetOutputFileHandle(OUT_FD, True)
    handle = debugger.GetOutputFileHandle()
    result.write('handle: %s'% handle.name)
    result.PutOutput(handle)


def bp_dict(debugger, command, result, internal_dict):
    """ return a breakpoint dict of form = {'filename:line_nr': [id, id, ...]} """
    target = lldb.debugger.GetSelectedTarget()
    id_dict = {}

    for bp in target.breakpoint_iter():
        for bl in bp:
            loc = bl.GetAddress().GetLineEntry()
            key = str(loc.GetFileSpec()) + ':' + str(loc.GetLine())
            if key in id_dict:
                id_dict[key].append(bp.GetID())
            else:
                id_dict[key] = [bp.GetID()]

    vimOutCb('breakpoint updated', id_dict)
    print(id_dict)

def line_at_frame(debugger, command, result, internal_dict):
    """ return the source file's line # based on a the selected frame """
    target = lldb.debugger.GetSelectedTarget()
    if target is not None:
        process = target.GetProcess()
        for thread in process:
            frame = thread.GetSelectedFrame()
            if frame is not None:
                path = frame.GetPCAddress().GetLineEntry()
                vimOutCb('current file', path)
    else:
        print("Unable to get a line entry for frame")



# TODO run in separate thread
# use logging callback to launch once an active thread is established
def EventThreadLoop(debugger):
    """ main loop to listen for LLDB events """
    event = lldb.SBEvent()
    listener = debugger.GetListener()
    done = False

    while not done:
        if listener.WaitForEvent(1, event):
            ev_mask = event.GetType()
            print('type: %s', ev_mask)



""" Parsing logs avoids the overhead of multithreading for an event loop """
def log_cb(msg):
    vimOutCb('logging', msg)


if __name__ == '__main__':
    # create a new debugger instance if running from CLI
    lldb.debugger = lldb.SBDebugger.Create()
elif lldb.debugger:
    # initialize global setup here
    # for lldb->vim comms use vimOutCb or logging or override HandleCommand globally?
    # apropros log
    lldb.debugger.SetPrompt('(vim-lldb)')
    lldb.debugger.SetLoggingCallback(log_cb)
    lldb.debugger.EnableLog('lldb', ['break'])

    lldb.debugger.HandleCommand('command script add -f lldb_commands.bp_dict bp_dict')
    print('The "bpdict" command has been installed')
    lldb.debugger.HandleCommand('command script add -f lldb_commands.line_at_frame line_at_frame')
    print('The "line_at_frame" command has been installed')
    lldb.debugger.HandleCommand('command script add -f lldb_commands.set_tty set_tty')
    print('The "set_tty" command has been installed')
    lldb.debugger.HandleCommand('command script add -f lldb_commands.get_tty get_tty')
    print('The "get_tty" command has been installed')

    if 0:
        t_events = Thread(target=EventThreadLoop, args=(lldb.debugger,))
        t_events.setDaemon(True)
        t_events.start()
        t_events.join()

