# TODO: check loading init files doesn't break anything, sourcemaps
# ref:
#  TestEvents.py
# Useful built-ins
#   Custom breakpoint functions: use to connect callbacks here
#   SBHostOS: GetLLDBPath, GetLLDBPythonPath, CreateThread



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


OUT_FD = __stdout__
IN_FD = __stdin__

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
    result.write('tty output: %s\n'% handle)
    handle = debugger.GetInputFileHandle()
    result.write('tty input: %s\n'% handle)
    result.PutOutput(handle)

def set_tty_in(debugger, command, result, internal_dict):
    """ redirect input file """
    args = shlex.split(command)
    global IN_FD
    IN_FD = __stdin__
    if len(args) > 0:
        path = args[0].strip()
        IN_FD = open(path, "r")

    debugger.SetInputFileHandle(IN_FD, True)
    handle = debugger.GetInputFileHandle()
    result.write('input redirected to fd: %s\n'% IN_FD.name)
    result.PutOutput(OUT_FD)

def set_tty_out(debugger, command, result, internal_dict):
    """ redirect output file """
    args = shlex.split(command)
    global OUT_FD
    OUT_FD = __stdout__
    if len(args) > 0:
        path = args[0].strip()
        OUT_FD = open(path, "w")

    debugger.SetOutputFileHandle(OUT_FD, True)
    debugger.SetErrorFileHandle(OUT_FD, False)
    handle = debugger.GetOutputFileHandle()
    result.write('output redirected to fd: %s\n'% OUT_FD.name)
    result.PutOutput(handle)

def line_at_frame(debugger, command, result, internal_dict):
    """ return the source file's line # based on a the selected frame """
    target = debugger.GetSelectedTarget()
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

def breakpoints(event):
    """ return a breakpoint dict of form = {'filename:line_nr': [id, id, ...]} """
    target = lldb.SBTarget_GetTargetFromEvent(event)
    #vimOutCb('bptarget', target)
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
                self.target = self.dbg.GetSelectedTarget()

                if self.target:
                    vimOutCb('target-set', self.target)
                    # valid target set so process events async
                    #self.dbg.SetAsync(True)

                if lldb.SBTarget_EventIsTargetEvent(event):
                    vimOutCb('basic target', 'none')
                    self.target = lldb.SBTarget_GetTargetFromEvent(event)
                    vimOutCb( 'target', self.dbg.GetSelectedTarget())

                if lldb.SBProcess_EventIsProcessEvent(event):
                    process = lldb.SBProcess().GetProcessFromEvent(event)
                    state = lldb.SBProcess_GetStateFromEvent(event)
                    if state == lldb.eStateExited:
                        vimOutCb( 'process:exited', self.dbg.StateAsCString(state))
                        done = True
                        # TODO clean up and alert vim
                        return


                    if state == lldb.eStateStopped:
                        vimOutCb('process stopped', state)



                    elif event_mask & lldb.SBProcess.eBroadcastBitStateChanged:
                        state_string = self.dbg.StateAsCString(state)
                        vimOutCb( 'process:bbitchanged', self.dbg.StateAsCString(state))

                    elif lldb.SBProcess_EventIsStructuredDataEvent(event):
                        state = lldb.SBProcess_GetStateFromEvent(event)
                        vimOutCb( 'process:data', self.dbg.StateAsCString(state))

                if lldb.SBBreakpoint_EventIsBreakpointEvent(event):
                    bp = lldb.SBBreakpoint_GetBreakpointFromEvent(event)
                    #bp_dict = breakpoints(event)
                    vimOutCb( 'breakpoint', bp)

                if lldb.SBTarget_EventIsTargetEvent(event):
                    vimOutCb( 'target', event)

def thread_result_t(message):
    print('thread_result_t: %s'% message)



# @TODO kill events thread when LLDB stops
if __name__ == '__main__':

    if not lldbImported:
        print('\033]51;["call","Lldbapi_%s", ["%s"]]\007' %
                ('LldbErrFatalCb', 'Failed to import vim-lldb. Try setting g:lldb_python_interpreter_path=\'path/to/python\' in .vimrc. See README for help.',))
        sys.exit()
    else:

        lldb.debugger = lldb.SBDebugger.Create(True)
        lldb.debugger.SetAsync(True)

        handle_events = True
        spawn_thread = False
        num_errors = 1
        quit_requested = True
        stopped_on_crash = True

        options = lldb.SBCommandInterpreterRunOptions()
        options.SetEchoCommands(True)
        options.SetStopOnError(False)
        options.SetStopOnCrash(False)
        options.SetStopOnContinue(False)
        options.SetPrintResults(False)

        lldb.debugger.RunCommandInterpreter(handle_events, spawn_thread, options, num_errors, quit_requested, stopped_on_crash)

        #t_error = lldb.SBError()
        #lldb.SBHostOS.ThreadJoin('lldb.debugger.io-handler', thread_result_t, t_error)

        t_events = EventListeningThread(lldb.debugger)
        lldb.SBHostOS_ThreadCreated('vim-lldb-events')

        t_events.start()
        t_events.join()


def __lldb_init_module(debugger, internal_dict):
    """ called when importing this module into the lldb interpreter """
    # (lldb) log list  - list channels/categories
    #debugger.SetLoggingCallback(log_cb)
    #debugger.EnableLog('lldb', ['break', 'target', 'step'])

    debugger.HandleCommand('command script add -f lldb_commands.line_at_frame line_at_frame')
    debugger.HandleCommand('command script add -f lldb_commands.set_tty_in set_tty_in')
    debugger.HandleCommand('command script add -f lldb_commands.set_tty_out set_tty_out')
    debugger.HandleCommand('command script add -f lldb_commands.get_tty get_tty')

    #debugger.SetOutputFileHandle(__stdout__, True)

