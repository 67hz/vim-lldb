# TODO: check loading init files doesn't break anything, sourcemaps
# Useful built-ins
#   Custom breakpoint functions: use to connect callbacks here
#   SBHostOS: GetLLDBPath, GetLLDBPythonPath



import lldb_path
import shlex
import optparse
import json
from sys import __stdout__, __stdin__
from re import compile, VERBOSE, search, sub
import threading

try:
    lldb_path.update_sys_path()
    import lldb
    lldbImported = True
except ImportError:
    lldbImported = False

OUT_FD = None

def JSON(obj):
    " create JSON from object and escape all quotes """
    return json.dumps(str(obj), ensure_ascii = True)

def vimOutCb(res, data = ''):
    """ Escape sequence to trap into Vim's cb channel.
        See :help term_sendkeys for job -> vim communication """
    print('\033]51;["call","Lldbapi_LldbOutCb", [{}, {}]]\007'.format(JSON(res), JSON(data)))

def vimErrCb(err):
    print('\033]51;["call","Lldbapi_LldbErrCb",["{}"]]\007'.format(JSON(err)))



#
# Define custom commands for LLDB
#

def get_tty(debugger, command, result, internal_dict):
    handle = debugger.GetOutputFileHandle()
    result.write('tty output: %s'% handle)
    result.PutOutput(handle)

def set_log_tty_in(debugger, command, result, internal_dict):
    """ redirect log output """
    args = shlex.split(command)
    global IN_FD
    IN_FD = __stdout__
    if len(args) > 0:
        path = args[0].strip()
        print('path:%s'% path)
        IN_FD = open(path, "r")

    debugger.SetInputFileHandle(IN_FD, True)
    handle = debugger.GetInputFileHandle()
    result.write('input redirected to fd: %s\n'% IN_FD.name)
    result.PutOutput(handle)

def set_log_tty_out(debugger, command, result, internal_dict):
    """ redirect log output """
    args = shlex.split(command)
    global OUT_FD
    OUT_FD = __stdout__
    if len(args) > 0:
        path = args[0].strip()
        print('path:%s'% path)
        OUT_FD = open(path, "w")

    debugger.SetOutputFileHandle(OUT_FD, True)
    handle = debugger.GetOutputFileHandle()
    result.write('output redirected to fd: %s\n'% OUT_FD.name)
    result.PutOutput(handle)

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
        vimErrCb("Unable to get a line entry for frame")



#
# custom helpers
#

def getSelectedFrame(debugger):
    frame = None
    for thread in debugger.GetSelectedTarget().GetProcess():
        frame = thread.GetSelectedFrame()

    return frame

def getLineEntryFromFrame(debugger):
    """ return full path from frame """
    frame = getSelectedFrame(debugger)
    path = frame.GetPCAddress().GetLineEntry()
    return path

def breakpoints(debugger):
    """ return a breakpoint dict of form = {'filename:line_nr': [id, id, ...]} """
    target = debugger.GetSelectedTarget()
    breakpoints = {}

    for bp in target.breakpoint_iter():
        for bl in bp:
            loc = bl.GetAddress().GetLineEntry()
            key = str(loc.GetFileSpec()) + ':' + str(loc.GetLine())
            #vimOutCb(JSON(key))
            if key in breakpoints:
                breakpoints[key].append(bp.GetID())
            else:
                breakpoints[key] = [bp.GetID()]

    return breakpoints



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


class EventListeningThread(threading.Thread):
    def __init__(self, debugger):
        threading.Thread.__init__(self)
        self.dbg = debugger

    def run(self):
        """ main loop to listen for LLDB events """
        listener = self.dbg.GetListener()
        event = lldb.SBEvent()
        done = False

        while not done:
            if listener.WaitForEvent(1, event):

                event_mask = event.GetType()
                #vimOutCb( 'event', event_mask)
                #vimOutCb( 'debugger', self.dbg)

                if lldb.SBBreakpoint_EventIsBreakpointEvent(event):
                   # bp = lldb.SBBreakpoint_GetBreakpointFromEvent(event)
                    bp_dict = breakpoints(self.dbg)
                    vimOutCb( 'breakpoint', bp_dict)

                if lldb.SBTarget_EventIsTargetEvent(event):
                    vimOutCb( 'target', event)

                if lldb.SBProcess_EventIsProcessEvent(event):
                    process = lldb.SBProcess().GetProcessFromEvent(event)
                    state = lldb.SBProcess_GetStateFromEvent(event)
                    vimOutCb( 'process:state', lldb.SBProcess.StateAsCString(state))

                    if event_mask & lldb.SBProcess.eBroadcastBitStateChanged:
                        vimOutCb( 'process:bbitchanged', lldb.SBProcess.StateAsCString(state))

                    if lldb.SBProcess_EventIsStructuredDataEvent(event):
                        state = lldb.SBProcess_GetStateFromEvent(event)
                        vimOutCb( 'process:data', lldb.SBProcess.StateAsCString(state))






""" Send logs off to Vim for parsing """
def log_cb(msg):
    # output logs for debugging only
    #print('OUTFD', OUT_FD)
    if OUT_FD:
        OUT_FD.write(msg)
        #vimOutCb('ParseLogs', 'lldb-log', msg)

    log_id = compile(r'\d*?\.\d*\s?')
    heading = compile('(\w*)\:\:(\w*)')
    header = search(heading, msg)
    
    # Below is a temp placeholder. This will be streamlined into a few basic flows based on select logging
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
            vimOutCb('current file', frame)
    elif header.group(1) == 'Process':
        if header.group(2) == 'PerformAction':
            frame = getLineEntryFromFrame()
            vimOutCb('current file', frame)




class LLDBThread(threading.Thread):
    def __init__(self, debugger):
        threading.Thread.__init__(self)
        self.dbg = debugger

    def run(self):
        self.dbg.SetPrompt('(vim-lldb)')
        # do not return from function until process stops during step/continue

        # (lldb) log list  - list channels/categories
        self.dbg.EnableLog('lldb', ['break', 'target', 'step'])
        #self.dbg.EnableLog('lldb', ['default'])
        #self.dbg.EnableLog('lldb', ['event'])
        #self.dbg.SetLoggingCallback(log_cb)
        # do not return from function until process stops during step/continue
        self.dbg.SetAsync(False)

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
        self.dbg.RunCommandInterpreter(handle_events, spawn_thread, options, num_errors, quit_requested, stopped_on_crash)


# @TODO kill events thread when LLDB stops
if __name__ == '__main__':

    if not lldbImported:
        print('\033]51;["call","Lldbapi_%s", ["%s"]]\007' %
                ('LldbErrFatalCb', 'Failed to import vim-lldb. Try setting g:lldb_python_interpreter_path=\'path/to/python\' in .vimrc. See README for help.',))
        sys.exit()
    else:
        lldb.debugger = lldb.SBDebugger.Create()
        t_lldb = LLDBThread(lldb.debugger)
        t_lldb.start()

        t_events = EventListeningThread(lldb.debugger)
        #t_events.setDaemon(True)
        t_events.start()
        t_lldb.join()
        t_events.join()





def __lldb_init_module(debugger, internal_dict):
    """ called when importing this module into the lldb interpreter """
    # for lldb->vim comms use vimOutCb or logging or override HandleCommand globally?
    # apropros log
    debugger.SetLoggingCallback(log_cb)
    #debugger.SetUseExternalEditor(True)

    # (lldb) log list  - list channels/categories
    debugger.EnableLog('lldb', ['break', 'target', 'step'])

    #debugger.HandleCommand('command script add -f lldb_commands.bp_dict bp_dict')
    debugger.HandleCommand('command script add -f lldb_commands.line_at_frame line_at_frame')
    debugger.HandleCommand('command script add -f lldb_commands.set_log_tty_in set_log_tty_in')
    debugger.HandleCommand('command script add -f lldb_commands.set_log_tty_out set_log_tty_out')
    debugger.HandleCommand('command script add -f lldb_commands.get_tty get_tty')

    #debugger.SetOutputFileHandle(__stdout__, True)

