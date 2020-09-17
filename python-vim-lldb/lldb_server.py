"""
see SBBroadcaster and SBEvent for example
SBTarget for breakpoint iterator
    * FindBreakpointsByID/Name
    * GetTargetFromEvent
"""
from __future__ import print_function

from os import system, name
import sys
import re
import lldb_path
from utility import *

try:
    lldb_path.update_sys_path()
    import lldb
    lldbImported = True
except ImportError:
    lldbImported = False


""" Free methods """

def clear():
    # windows
    if name == 'nt':
        _ = system('cls')
    else:
        _ = system('clear')

def backline(i):
    CURSOR_UP = '\x1b[1A'
    ERASE_LINE = '\x1b[2K'
    while i > 0:
        print(CURSOR_UP + ERASE_LINE)
        i -= 1

def escapeQuotes(res):
    res = escape_ansi(res.encode("utf-8", "replace"))
    res = str(res.decode("utf-8"))
    res = res.replace('"', '\\\"')
    return res

def parseArgs(data):
    args = data.split(' ')
    return args

""" Escape sequence to trap into Vim's cb channel.
    See :help term_sendkeys for job -> vim communication """
def vimOutCb(res, data = ''):
    print('\033]51;["call","Lldbapi_LldbOutCb", ["{}", "{}"]]\007'.format(escapeQuotes(res), data))

def vimErrCb(err):
    print('\033]51;["call","Lldbapi_LldbErrCb",["{}"]]\007'.format(escapeQuotes(err)))



""" Manage lifecycle of lldb instance"""
class LLDB(object):
    def __init__(self):
        self.dbg = None
        self.target = None
        self.process = None
        self.ci = None
        self.isActive = False

    def start(self):
        self.dbg = lldb.SBDebugger.Create()
        # do not return from function until process stops during step/continue
        self.dbg.SetAsync(False)
        self.ci = self.dbg.GetCommandInterpreter()

    def setTarget(self):
        target = self.dbg.GetSelectedTarget()
        if target.IsValid():
            self.target = target
            print('target set')
        else:
            print('target invalid')

    def startListener(self):
        event = lldb.SBEvent()
        broadcaster = self.process.GetBroadcaster()
        listener = lldb.SBListener('dbg listener')
        rc = broadcaster.AddListener(listener, lldb.SBProcess.eBroadcastBitStateChanged)
        if listener.WaitForEventForBroadcasterWithType(5,
                broadcaster,
                lldb.SBProcess.eBroadcastBitStateChanged,
                event):
            desc = lldbutil.get_description(event)
            print('Event desc: %s', desc)
        else:
            print('no event')

    def setProcess(self):
        self.process = self.target.GetProcess()

    def getProcessState(self):
        if self.process is not None:
            state = self.process.GetState() 
            return self.dbg.StateAsCString(state)
        else:
            return None

    def getPid(self):
        if self.process is not None and self.process.IsValid():
            return self.process.GetProcessID()
        else:
            return None

    def terminate(self):
        self.dbg.Terminate()
        self.dbg = None


    def syncSession(self, res):
        """ lldb handles the task of lauching/attaching relieving this module from a priori knowledge of target reqs and custom settings. We only establish a target after lldb returns from a command with a target instead of creating a target to pass off to lldb """
        # attempt to set target if no target (valid) exists or
        # an exec is explicitly set
        if self.target is None or 'executable set' in str(res):
            self.setTarget()

            # unset pre-existing process to make sure we sync to the newest process
            self.process = None

        elif self.getPid() is None:
            self.setProcess()
            #print('pid: %s'% self.getPid())

    def getCommandResult(self, data):
        res = lldb.SBCommandReturnObject()
        cmd = data.replace('\n', ' ').replace('\r', '')
        self.ci.HandleCommand(cmd, res)
        self.syncSession(res)

        return res

    def getFrame(self):
        for thread in self.process:
            for frame in thread:
                print(frame)

    def getLineEntryFromFrame(self):
        """ return full path from frame """
        for thread in self.process:
            frame = thread.GetSelectedFrame()
            path = frame.GetPCAddress().GetLineEntry()
            return path

    def getBreakpointAtFileLine(self, data):
        args = parseArgs(data)
        filename = args[1]
        line_nr = args[2]
        self.getAllBreakpoints()

    def getActiveBreakpointIDs(self):
        """ return all active bp id's as list [id, id, ...] """
        ids = []
        for bp in self.target.breakpoint_iter():
            ids.append(bp.GetID())

        return {"ids": ids}

    def getBreakpointDict(self):
        """ REVIEW is it necessary to store sub-ids of breakpoint, e.g. 1.2
          id_dict = {'filename:line_nr': [id, id, ...]} """
        id_dict = {}

        for bp in self.target.breakpoint_iter():
            for bl in bp:
                loc = bl.GetAddress().GetLineEntry()
                key = str(loc.GetFileSpec()) + ':' + str(loc.GetLine())
                if key in id_dict:
                    id_dict[key].append(bp.GetID())
                else:
                    id_dict[key] = [bp.GetID()]

        return id_dict



"""
@TODO
* handle keyboard interrupt
* add tab-completion
* add command history, last command toggle
* add 'Finish' command to end debugger session
* add 'clear' screen
* respawn on error or user request
* define arg flags (e.g., '--internal', ...)

Start LLDB interpreter in IO loop to take commands from input prompt
and pass to debugger instance
"""
def startIOLoop(outcb, errcb):
    dbg = LLDB()
    dbg.start()
    flag_internal = '--internal'

    while True:
        data = input("(lldb) ")

        """ internal commands skip lldb's CI """
        if flag_internal in data:
            backline(1)

            data.replace(flag_internal, '')
            if 'bp_frame' in str(data):
                dbg.getFrame()
                continue
            if 'bp_ids' in str(data):
                outcb('breakpoint all-ids', dbg.getActiveBreakpointIDs())
                continue
            if 'bp_sync' in str(data):
                outcb('breakpoint updated', dbg.getBreakpointDict())
                continue
            if 'frame_path' in str(data):
                outcb('current file', dbg.getLineEntryFromFrame())
                continue

        if len(data) < 1:
            continue

        res = dbg.getCommandResult(data)

        if res.Succeeded():
            output = res.GetOutput()
            outcb(output)
        else:
            output = res.GetError()
            errcb(output)

        print('(lldb) %s'% output)

    dbg.Terminate()



# start LLDB interpreter if lldb was imported
if not lldbImported:
    print('\033]51;["call","Lldbapi_%s", ["%s"]]\007' %
            ('LldbErrFatalCb', 'Failed to import vim-lldb. Try setting g:lldb_python_interpreter_path=\'path/to/python\' in .vimrc. See README for help.',))
else:
    startIOLoop(vimOutCb, vimErrCb)

