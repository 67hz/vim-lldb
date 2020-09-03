from __future__ import print_function

import os
import sys
import lldb_path

try:
    lldb_path.update_sys_path()
    import lldb
    lldbImported = True
except ImportError:
    lldbImported = False


log = open('lldb_server.log', 'a')
log.write("\n\nnew run\n\n")


""" @TODO this will handle switch logic for updating vim """
""" see :help term_sendkeys for job > vim communication """
def sendResToVim(res):
    #print('\033]51;["call","Tapi_%s", ["%s"]]\007' % (method, str(args)))
    print('\033]51;["call","Tapi_%s", ["%s"]]\007' % ('Test', 'placeholder'))



class LLDB(object):
    """ Manage lifecycle of lldb instance"""
    def __init__(self):
        self.dbg = None
        self.target = None
        self.process = None
        self.thread = None
        self.frame = None
        self.ci = None

    def start(self):
        self.dbg = lldb.SBDebugger.Create()
        # do not return from function until process stops during step/continue
        self.dbg.SetAsync(False)
        self.ci = self.dbg.GetCommandInterpreter()

    def terminate():
        self.dbg.Terminate()
        self.dbg = None

    def getCommandResult(self, data):
        res = lldb.SBCommandReturnObject()
        cmd = data.replace('\n', ' ').replace('\r', '')
        self.ci.HandleCommand(cmd, res)

        log.write('%s'% str(res))
        return res


"""
@TODO
* handle keyboard interrupt
* add tab-completion
* add 'clear' screen
* comm -> vim using Tapi
* respawn on error or user request

Start LLDB interpreter and IO loop to take commands from input prompt
and pass to debugger instance
"""
def startIOLoop(outcb):
    dbg = LLDB()
    dbg.start()
    log.write('IO Server started')

    while True:
        data = input("(lldb) ")
        if data == 'Finish':
            return

        if len(data) < 1:
            continue

        res = dbg.getCommandResult(data)
        if res.Succeeded():
            res = res.GetOutput()
        else:
            res = res.GetError()

        print('%s'% res)
        outcb(res)

    dbg.Terminate()



# start LLDB interpreter
if not lldbImported:
    print('\033]51;["call","Tapi_%s", ["%s"]]\007' %
            ('Error', 'Failed to import vim-lldb. See README for help',))
else:
    startIOLoop(sendResToVim)

