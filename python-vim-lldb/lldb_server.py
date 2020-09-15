"""
see SBBroadcaster and SBEvent for example
SBTarget for breakpoint iterator
    * FindBreakpointsByID/Name
    * GetTargetFromEvent
"""
from __future__ import print_function

import os
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


def escapeQuotes(res):
    res = escape_ansi(res.encode("utf-8", "replace"))
    #res = str(res.decode("utf-8")).replace("'", "''")
    res = str(res.decode("utf-8"))
    return res

def parseArgs(data):
    args = data.split(' ')
    return args

""" @TODO this will handle switch logic for updating vim
    should indicate if UI update is required? call Tapi_x(method, args, {updates})
    consider move to sep moduls and DI lldb
    see :help term_sendkeys for job > vim communication
    """
def vimOutCb(res, pid, state):
    print('\033]51;["call","Tapi_LldbOutCb", ["{}"]]\007'.format(escapeQuotes(res)))


def vimErrCb(err):
    print('\033]51;["call","Tapi_LldbErrCb",["{}"]]\007'.format(escapeQuotes(err)))




class LLDB(object):
    """ Manage lifecycle of lldb instance"""
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
        #self.process = self.ci.GetProcess()

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

    """ run follow up logic after every command. useful for attach/detach """
    def commandResultManager(self, res):
        if self.target is None or 'executable set' in str(res):
            self.setTarget()
            # unset pre-existing process 
            self.process = None

        elif self.getPid() is None:
            self.setProcess()
            #self.startListener()
            print('pid: %s'% self.getPid())

    def getCommandResult(self, data):
        res = lldb.SBCommandReturnObject()
        cmd = data.replace('\n', ' ').replace('\r', '')
        self.ci.HandleCommand(cmd, res)

        self.commandResultManager(res)

        return res

    def getBreakpointAtFileLine(self, data):
        args = parseArgs(data)
        filename = args[1]
        line_nr = args[2]
        print('filename: {} line_nr: {}'.format(filename, line_nr))
        self.getAllBreakpoints()



    """ SBTarget supports module, breakpoint, watchpoint iters """
    """ maintain breakpoints for easier access for outsiders, e.g, vim """
    def getAllBreakpoints(self):
        for b in self.target.breakpoint_iter():
            print(b)
            loc = b.FindLocationByID(b.GetID())
            """
                regex file, line from breakpoint
                else
                    regex from GetLineEntry
                """
            if loc:
                filename = loc.GetAddress().GetLineEntry()
                print("Abs file path: %s"% filename)




"""
@TODO
* handle launch/attach/set target

* handle keyboard interrupt
* add tab-completion
* add command history, last command toggle
* add 'clear' screen
* respawn on error or user request
* define arg flags (e.g., '--internal', ...)

Start LLDB interpreter and IO loop to take commands from input prompt
and pass to debugger instance
"""
def startIOLoop(outcb, errcb):
    dbg = LLDB()
    dbg.start()
    flag_internal = '--internal'

    while True:
        data = input("(lldb) ")

        if data == 'Finish':
            return

        """ internal commands skip lldb's CI """
        if flag_internal in data:
            data.replace(flag_internal, '')
            if 'bp_all' in data:
                dbg.getAllBreakpoints()
                continue
            if 'bp_at' in str(data):
                dbg.getBreakpointAtFileLine(data)
                continue

        if len(data) < 1:
            continue

        # @TODO strip any flags from data
        res = dbg.getCommandResult(data)

        if res.Succeeded():
            output = res.GetOutput()
            outcb(output, dbg.getPid(), dbg.getProcessState())
        else:
            output = res.GetError()
            errcb(output)

        print('(lldb) %s'% output)

    dbg.Terminate()



# start LLDB interpreter
if not lldbImported:
    print('\033]51;["call","Tapi_%s", ["%s"]]\007' %
            ('LldbErrCb', 'Failed to import vim-lldb. See README for help',))
else:
    startIOLoop(vimOutCb, vimErrCb)

