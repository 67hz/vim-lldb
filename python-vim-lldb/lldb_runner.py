from __future__ import print_function

from os import system, name
from re import compile, VERBOSE
import sys
import lldb_path

try:
    lldb_path.update_sys_path()
    import lldb
    lldbImported = True
except ImportError:
    lldbImported = False


# 7/8-bit C1 ANSI sequences
ansi_escape = compile(
    br'(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])'
)

def escape_ansi(line):
    return ansi_escape.sub(b'', bytes(line))

def clear():
    # windows
    if name == 'nt':
        _ = system('cls')
    else:
        _ = system('clear')

def removeLastNLines(i):
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



""" Manage an lldb instance"""
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

    def getCommandResult(self, data, add_to_history = False):
        res = lldb.SBCommandReturnObject()
        cmd = data.replace('\n', ' ').replace('\r', '')
        self.ci.HandleCommand(cmd, res, add_to_history)
        self.syncSession(res)

        return res

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
* add 'Finish' command to end debugger session
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

        if len(data) < 1:
            continue

        """ internal commands skip lldb's CI """
        if flag_internal in data:
            removeLastNLines(1)

            data.replace(flag_internal, '')
            if 'bp_ids' in str(data):
                outcb('breakpoint all-ids', dbg.getActiveBreakpointIDs())
            elif 'bp_sync' in str(data):
                outcb('breakpoint updated', dbg.getBreakpointDict())
            elif 'frame_path' in str(data):
                outcb('current file', dbg.getLineEntryFromFrame())
            elif 'clear' in str(data):
                clear()
            elif 'wipe' in str(data):
                continue
            elif 'finish' in str(data):
                return

        else:
            res = dbg.getCommandResult(data, True)

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
