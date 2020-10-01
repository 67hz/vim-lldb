# TODO: check loading init files doesn't break anything, sourcemaps
# ref:
#  lldb_enumerations.h
#  TestEvents.py
# Useful built-ins
#   Custom breakpoint functions: use to connect callbacks here
#   SBHostOS: GetLLDBPath, GetLLDBPythonPath, CreateThread



from __future__ import print_function
import lldb_path
import shlex
import optparse
import json
from sys import __stdout__, __stdin__, __stderr__, stdout, stdin, stderr
from re import compile, VERBOSE, search, sub
from time import sleep
import threading

try:
    lldb_path.update_sys_path()
    from lldb import *
    lldbImported = True
except ImportError:
    lldbImported = False


LINE_MAX = 1024
stdout_buffer = ''
stdin_buffer = ''
OUT_FD = __stdout__
IN_FD = __stdin__
ERR_FD = __stderr__
debugger = None
process = None
target = None
output_event_listener = None
printer = print
broadcaster = None

event_has_process = threading.Event()



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
    result.write('tty output: %s\n'% OUT_FD)
    handle = debugger.GetInputFileHandle()
    result.write('tty input: %s\n'% IN_FD)
    result.PutOutput(handle)

def set_tty_in(debugger, command, result, internal_dict):
    """ redirect input file """
    args = shlex.split(command)
    global IN_FD
    if len(args) > 0:
        path = args[0].strip()
        IN_FD = open(path, "r")

    debugger.SetInputFileHandle(IN_FD, True)
    handle = debugger.GetInputFileHandle()
    result.write('input redirected to fd: %s\n'% IN_FD.name)

def set_tty_out(debugger, command, result, internal_dict):
    """ redirect output file """
    args = shlex.split(command)
    global OUT_FD
    OUT_FD = __stdout__
    if len(args) > 0:
        path = args[0].strip()
        OUT_FD = open(path, "w")

    debugger.SetOutputFileHandle(OUT_FD, True)
    debugger.SetErrorFileHandle(OUT_FD, True)
    handle = debugger.GetOutputFileHandle()
    result.write('output redirected to fd: %s\n'% OUT_FD.name)
    #result.PutOutput(handle)

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
    target = SBTarget_GetTargetFromEvent(event)
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
    stream = SBStream()
    get_desc_method = getattr(obj, 'GetDescription')

    tuple = (SBTarget, SBBreakpointLocation, SBWatchpoint)
    if isinstance(obj, tuple):
        if option is None:
            option = eDescriptionLevelVerbose

    if option is None:
        success = get_desc_method(stream)
    else:
        success = get_desc_method(stream, option)

    if not success:
        return None

    return stream.GetData()

def requestStart(process, event):
    # TODO need a way to continue based on user input
    #listen for enter key
    cont = input('continue process [y/n]:')
    if 'y' in cont:
        print('continuing process')
        error = process.Continue()


        if not error.Success():
            print('could not start process')



class EventListeningThread(threading.Thread):
    def run(self):
        global stdout_buffer
        """ main loop to listen for LLDB events """
        listener = debugger.GetListener()
        #broadcaster = debugger.GetCommandInterpreter().GetBroadcaster()
        event = SBEvent()
        process = None
        done = False
        state_prev = None

        while not done:
            if listener.WaitForEvent(1, event):
                event_mask = event.GetType()
                self.target = debugger.GetSelectedTarget()
                printer('event', getDescription(event))
                printer('flavor', event.GetDataFlavor())

                if SBTarget_EventIsTargetEvent(event):
                    self.target = SBTarget_GetTargetFromEvent(event)
                    printer( 'target', debugger.GetSelectedTarget())

                if SBProcess_EventIsProcessEvent(event):
                    process = SBProcess().GetProcessFromEvent(event)
                    printer('set process event')
                    event_has_process.set()

                    if process.eBroadcastBitStateChanged:
                        state = SBProcess_GetStateFromEvent(event)
                        if state_prev is not None:
                            printer('old state:', debugger.StateAsCString(state_prev))
                            printer('new state:', debugger.StateAsCString(state))
                            # TODO add diff logic before setting

                        state_prev = state


                        printer( 'process:bbitchanged', debugger.StateAsCString(state))
                        if event_mask & eStateRunning:
                            printer('run')
                            # read input or allow process to resume
                            #process.PutSTDIN('foo')
                            continue
                            #process.Clear()

                        if event_mask & eStateStopped:
                            stopid = process.GetStopID()
                            for t in process:
                                if t.GetStopReason() == eStopReasonBreakpoint:
                                    printer('bp stop')
                                if t.GetStopReason() == 8:
                                    printer('stopped at 8')
                                    #process.Continue()
                                if t.GetStopReason() == 3:
                                    printer('stopped at 3')

                                printer('t desc', t.GetStopReason())


                            t = process.GetSelectedThread()
                            t.Resume()
                            continue


                        if event_mask & (SBProcess.eBroadcastBitSTDOUT |
                                SBProcess.eBroadcastBitSTDERR):
                            if event_mask & 0x4:
                                result = process.GetSTDOUT(LINE_MAX)
                                stdout_buffer += result
                                debugger.SetInputFileHandle(IN_FD, True)
                            else:
                                stream = SBStream()
                                event.GetDescription(stream)
                                printer('output_event', stream.GetData())
                                printer('stderr', process.GetSTDERR(LINE_MAX))

                            """
                            if event_mask & eStateRunning:
                                if event_mask & eInputReaderEndOfFile:
                                    printer('EOF')
                                    # TODO switch to process input
                                    """


                # 0x04 = quit type - where is this defined - not in lldb-enumerations.h???
                #if event_mask & 0x04 and False:
                if SBCommandInterpreter_EventIsCommandInterpreterEvent(event):
                    printer('\n\nCI event', event)
                    continue

                if event_mask & 0x04 and SBCommandInterpreter_EventIsCommandInterpreterEvent(event):
                    printer('exited request with process', process)
                    if process is not None and process.IsValid():
                        printer('procsess IsValid', process.IsValid())
                        process.Kill()

                    return



def thread_result_t(message):
    print('thread_result_t: %s'% message)


def _stop_event():
    global process
    Forever = True
    printer('broadcaster stop events', broadcaster.EventTypeHasListeners(SBProcess.eBroadcastBitStateChanged))
    event = SBEvent()

    while Forever:
        if not stop_event_listener:
            return

        if stop_event_listener.WaitForEventForBroadcasterWithType(1,
                broadcaster, SBProcess.eBroadcastBitStateChanged, event):
            printer('got event')
            event_mask = event.GetType()
            printer('SE', event_mask)


def _io_loop():
    pass


def _output_event():
    #global OUT_FD, ERR_FD
    global process
    Forever = True
    #broadcaster = debugger.GetCommandInterpreter().GetBroadcaster()
    printer('broadcaster', broadcaster.EventTypeHasListeners(SBProcess.eBroadcastBitSTDERR | SBProcess.eBroadcastBitSTDOUT))
    event = SBEvent()

    while Forever:

        if not output_event_listener:
            return

        if output_event_listener.WaitForEventForBroadcasterWithType(1,
                broadcaster,
                SBProcess.eBroadcastBitSTDOUT | SBProcess.eBroadcastBitSTDERR,
                event):
            event_mask = event.GetType()
            printer('OE', event_mask)

            if not process:
                process = SBProcess.GetProcessFromEvent(event)
                printer('no process', process)


            if event_mask & 0x4:
                result = process.GetSTDOUT(LINE_MAX)
                if result:
                    stdout_buffer += result
                    printer('stdout_buffer:')
                    printer(stdout_buffer)
                    process.Continue()

                else:
                    stream = SBStream()
                    event = event.GetDescription(stream)
                    printer("_output_event", stream.GetData())
                    printer("_stderr", process.GetSTDERR(LINE_MAX))





if __name__ == '__main__':
    if not lldbImported:
        print('\033]51;["call","Lldbapi_%s", ["%s"]]\007' %
                ('LldbErrFatalCb', 'Failed to import vim- Try setting g:lldb_python_interpreter_path=\'path/to/python\' in .vimrc. See README for help.',))
        sys.exit()
    else:

        debugger = SBDebugger.Create()
        debugger.SetAsync(True)

        # Temp Switch for vim
        printer = vimOutCb

        spawn_thread = True
        handle_events = True
        num_errors = 0
        quit_requested = True
        stopped_on_crash = False

        options = SBCommandInterpreterRunOptions()
        options.SetEchoCommands(True)
        options.SetStopOnError(False)
        options.SetStopOnCrash(False)
        options.SetStopOnContinue(False)
        options.SetPrintResults(True)
        options.SetAddToHistory(True)

        # create listeners
        #t_events = EventListeningThread()
        output_event_listener = SBListener('output-listener')
        stop_event_listener = SBListener('stop-listener')
        broadcaster = debugger.GetCommandInterpreter().GetBroadcaster()
        event = SBEvent()
        #debugger.HandleProcessEvent(process, event, OUT_FD, ERR_FD)

        broadcaster.AddListener(output_event_listener, SBProcess.eBroadcastBitSTDOUT | SBProcess.eBroadcastBitSTDERR)
        broadcaster.AddListener(stop_event_listener, SBProcess.eBroadcastBitStateChanged)

        #t_events.start()
        debugger.RunCommandInterpreter(handle_events, spawn_thread, options, num_errors, quit_requested, stopped_on_crash)

        threading.Thread(target=_output_event, name='output_event_listener', args=()).start()


        sleep(10)
        threading.Thread(target=_stop_event, name='stop_event_listener', args=()).start()
        process = debugger.GetCommandInterpreter().GetProcess()

        print('afterall')




        #t_events.join()




def log_cb(message):
    printer(message)


def __lldb_init_module(debugger, internal_dict):
    """ called when importing this module into the lldb interpreter """
    # (lldb) log list  - list channels/categories
    #debugger.SetLoggingCallback(log_cb)
    #debugger.EnableLog('lldb', ['process'])

    debugger.HandleCommand('command script add -f lldb_commands.line_at_frame line_at_frame')
    debugger.HandleCommand('command script add -f lldb_commands.set_tty_in set_tty_in')
    debugger.HandleCommand('command script add -f lldb_commands.set_tty_out set_tty_out')
    debugger.HandleCommand('command script add -f lldb_commands.get_tty get_tty')

    #debugger.SetOutputFileHandle(__stdout__, True)



