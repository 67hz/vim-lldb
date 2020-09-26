#!/usr/bin/python

# TODO: check loading init files doesn't break anything, sourcemaps
# Useful built-ins:
#   SBHostOS: GetLLDBPath, GetLLDBPythonPath



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

    print(id_dict)
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



#
# custom query helpers
#

def getSelectedFrame():
    frame = None
    for thread in lldb.debugger.GetSelectedTarget().GetProcess():
        frame = thread.GetSelectedFrame()

    return frame

def getLineEntryFromFrame():
    """ return full path from frame """
    frame = getSelectedFrame()
    path = frame.GetPCAddress().GetLineEntry()
    return path

def GetEvents(listener, broadcaster, num_tries):
    event = lldb.SBEvent()
    print('ETHS: %s'% broadcaster.EventTypeHasListeners(5))

    while True:
        if listener.WaitForEventForBroadcasterWithType(5, broadcaster, lldb.SBProcess.eBroadcastBitStateChanged):
            ev_mask = event.GetType()
            print('got event')
            print('event type: %s'% ev_mask)
            break
        num_tries -= 1
        if num_tries == 0:
            break


    listener.Clear()
    return


#
# lldb utils
#
def getDescription(obj, option = None):
    if obj is None:
        return None

    desc = None
    stream = lldb.SBStream()
    get_desc_method = getattr(obj, 'GetDescription')

    tuple = (lldb.SBTarget, lldb.SBBreakpointLocation, lldb.SBWatchpoint)
    if isinstance(obj, tuple):
        if option is None:
            option = lldb.eDescriptionLevelVerbose

    if option is None:
        success = get_desc_method(stream)
    else:
        success = get_desc_method(stream, option)

    if not success:
        return None

    return stream.GetData()

# use logging callback to launch once an active thread is established
class EventListeningThread(threading.Thread):
    def run(self):
        """ main loop to listen for LLDB events """
        event = lldb.SBEvent()
        Event
        listener = lldb.debugger.GetListener()
        num_tries = 2

        #GetEvents(listener, num_tries)
        return


def listen():
    listener = lldb.debugger.GetListener()
    process = lldb.debugger.GetSelectedTarget().GetProcess()
    print('Target: %s'% lldb.debugger.GetSelectedTarget())

    if process is not None:
        print('process: %s'% lldb.debugger.StateAsCString(process.GetState()))
        broadcaster = process.GetBroadcaster()
        event = lldb.SBEvent()
        listener = lldb.SBListener('my listener')
        rc = broadcaster.AddListener(listener, lldb.SBProcess.eBroadcastBitStateChanged)

        if rc == 1:
            print('rc: %s'% rc)
            GetEvents(listener, broadcaster, 4)
        



""" Send logs off to Vim for parsing """
def log_cb(msg):
    # output logs for debugging only
    if OUT_FD:
        OUT_FD.write(msg)
        #vimOutCb('ParseLogs', 'lldb-log', msg)

    log_id = compile(r'\d*?\.\d*\s?')
    heading = compile('(\w*)\:\:(\w*)')
    header = search(heading, msg)
    
    # Below is a temp placeholder. This should be streamlined into a few basic flows based on select logging
    if not header:
        cmd = compile(r'(?<=lldb)\s*(\w*\s*\w*)')
        header = search(cmd, msg)
        #print('cmd: ', header.group(0))
        if header.group(0).strip() == 'Added location':
            lldb.debugger.HandleCommand('bp_dict')
        return

    #print('parent: ', header.group(1))
    #print('sub: ', header.group(2))

    if header.group(1) == 'Target':
        if header.group(2) == 'Target':
            #print('New Target')
            return
        if header.group(2) == 'AddBreakpoint':
            # bps not ready yet
            return
        if header.group(2) == 'DisableBreakpointByID':
            # bps not ready yet
            lldb.debugger.HandleCommand('bp_dict')
            return

    elif header.group(1) == 'ThreadList':
        if header.group(2) == 'ShouldStop':
            frame = getLineEntryFromFrame()
            print('le: ', frame)
            vimOutCb('OutCb','current file', frame)
    elif header.group(1) == 'Process':
        if header.group(2) == 'PerformAction':
            frame = getLineEntryFromFrame()
            vimOutCb('OutCb','current file', frame)


    eventListener()



class LLDB():
    """ Wrapper for an LLDB instance """

    def __init__(self):
        """ set up a blank debugger instance. let the user decide options, targets,... """
        lldb.debugger = lldb.SBDebugger.Create()
        #self.ci = lldb.debugger.GetCommandInterpreter()
        lldb.debugger.SetPrompt('(vim-lldb)')
        # do not return from function until process stops during step/continue
        lldb.debugger.SetAsync(False)

        # (lldb) log list  - list channels/categories
        lldb.debugger.EnableLog('lldb', ['break', 'target', 'step'])
        #lldb.debugger.EnableLog('lldb', ['default'])
        #lldb.debugger.EnableLog('lldb', ['event'])
        lldb.debugger.SetLoggingCallback(log_cb)

        handle_events = True
        spawn_thread = False
        num_errors = 10
        quit_requested = True
        stopped_on_crash = True
        options = lldb.SBCommandInterpreterRunOptions()
        options.SetEchoCommands(True)
        options.SetStopOnError(False)
        options.SetStopOnCrash(False)
        options.SetStopOnContinue(True)
        options.SetPrintResults(True)


        result = lldb.debugger.RunCommandInterpreter(handle_events, spawn_thread, options, num_errors, quit_requested, stopped_on_crash)

        #lldb.debugger.HandleCommand('command script add -f lldb_commands.set_log_tty set_log_tty')
        lldb.debugger.HandleCommand('command script add -f lldb_commands.get_tty get_tty')
        print('result of running %s'% result)





"""
        self.dbg.HandleCommand('command script add -f lldb_commands.bp_dict bp_dict')
        print('The "bpdict" command has been installed')
        self.dbg.HandleCommand('command script add -f lldb_commands.line_at_frame line_at_frame')
        print('The "line_at_frame" command has been installed')
        self.dbg.HandleCommand('command script add -f lldb_commands.set_log_tty set_log_tty')
        print('The "set_log_tty" command has been installed')
        self.dbg.HandleCommand('command script add -f lldb_commands.get_tty get_tty')
        print('The "get_tty" command has been installed')
        global lldb.debugger
        lldb.debugger = self.dbg
        """

if __name__ == '__main__':
    lldb.debugger = lldb.SBDebugger.Create()
    #self.ci = lldb.debugger.GetCommandInterpreter()
    lldb.debugger.SetPrompt('(vim-lldb)')
    # do not return from function until process stops during step/continue
    lldb.debugger.SetAsync(False)

    # (lldb) log list  - list channels/categories
    lldb.debugger.EnableLog('lldb', ['break', 'target', 'step'])
    #lldb.debugger.EnableLog('lldb', ['default'])
    #lldb.debugger.EnableLog('lldb', ['event'])
    lldb.debugger.SetLoggingCallback(log_cb)

    handle_events = True
    spawn_thread = False
    num_errors = 10
    quit_requested = True
    stopped_on_crash = True
    options = lldb.SBCommandInterpreterRunOptions()
    options.SetEchoCommands(True)
    options.SetStopOnError(False)
    options.SetStopOnCrash(False)
    options.SetStopOnContinue(True)
    options.SetPrintResults(True)


    lldb.debugger.RunCommandInterpreter(handle_events, spawn_thread, options, num_errors, quit_requested, stopped_on_crash)






def __lldb_init_module(debugger, internal_dict):
    """ called when importing this module into the lldb interpreter """
    # for lldb->vim comms use vimOutCb or logging or override HandleCommand globally?
    # apropros log
    debugger.SetLoggingCallback(log_cb)

    # (lldb) log list  - list channels/categories
    debugger.EnableLog('lldb', ['break', 'target', 'step'])
    #lldb.debugger.EnableLog('lldb', ['default'])
    #lldb.debugger.EnableLog('lldb', ['event'])

    debugger.HandleCommand('command script add -f lldb_commands.bp_dict bp_dict')
    print('The "bpdict" command has been installed')
    debugger.HandleCommand('command script add -f lldb_commands.line_at_frame line_at_frame')
    print('The "line_at_frame" command has been installed')
    debugger.HandleCommand('command script add -f lldb_commands.set_log_tty set_log_tty')
    print('The "set_log_tty" command has been installed')
    debugger.HandleCommand('command script add -f lldb_commands.get_tty get_tty')
    print('The "get_tty" command has been installed')

    debugger.SetOutputFileHandle(__stdout__, True)

    if 0:
        eventsThread = EventListeningThread()
        #eventsThread.context = debugger
        eventsThread.setDaemon(True)
        eventsThread.start()
        eventsThread.join()




