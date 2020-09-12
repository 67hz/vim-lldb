"""
see SBBroadcaster and SBEvent for example
"""
from __future__ import print_function

import os
import sys
import lldb_path
from utility import *

try:
    lldb_path.update_sys_path()
    import lldb
    lldbImported = True
except ImportError:
    lldbImported = False


log = open('lldb_server.log', 'w')
log.write("\n\nnew run\n\n")


def escapeQuotes(res):
    res = escape_ansi(res.encode("utf-8", "replace"))
    res = str(res.decode("utf-8")).replace("'", "''")
    return res

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
        self.broadcaster = None
        self.isActive = False

    def start(self):
        self.dbg = lldb.SBDebugger.Create()
        self.target = self.dbg.CreateTarget('')
        # do not return from function until process stops during step/continue
        self.dbg.SetAsync(False)
        self.ci = self.dbg.GetCommandInterpreter()

    def setTarget(self):
        self.target = lldb.SBTarget()
        #print("lldb.target: %s"% lldb.target)
        #print("self.target: %s"% self.target)
        self.process = self.ci.GetProcess()
        self.broadcaster = self.process.GetBroadcaster()

    def getProcess(self):
        return self.ci.GetProcess()

    def getProcessState(self):
        state = self.getProcess().GetState() 
        return self.dbg.StateAsCString(state)

    def getBroadcaster(self):
        return self.getProcess().GetBroadcaster()

    def getPid(self):
        return self.getProcess().GetProcessID()

    def terminate():
        self.dbg.Terminate()
        self.dbg = None

    def getCommandResult(self, data):
        res = lldb.SBCommandReturnObject()
        cmd = data.replace('\n', ' ').replace('\r', '')
        self.ci.HandleCommand(cmd, res)
        log.write('%s'% str(res))
        log.write('gps: %s'% self.getProcessState())

        if self.getProcessState() == 'connected':
            print("Connected")

        return res


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
    log.write('IO Server started\n')

    while True:
        data = input("(lldb) ")
        if data == 'Finish':
            return

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

        # do not output response to console or run cb - useful for UI queries
        if flag_internal not in data:
            print('(lldb) %s'% output)

    dbg.Terminate()



# start LLDB interpreter
if not lldbImported:
    print('\033]51;["call","Tapi_%s", ["%s"]]\007' %
            ('LldbErrCb', 'Failed to import vim-lldb. See README for help',))
else:
    startIOLoop(vimOutCb, vimErrCb)

