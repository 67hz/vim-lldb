from __future__ import print_function

from os import system, name
from re import compile, VERBOSE, search, sub
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
    res = res.replace("'", '\\\"')
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



""" Manage an LLDB instance"""
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
        self.target = self.dbg.GetSelectedTarget()

    def setProcess(self):
        if self.target is not None:
            self.process = self.target.GetProcess()

    def processState(self):
        if self.process is None:
            self.process = self.setProcess()

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
        # attempt to set target if no target (valid) exists or
        # an exec is explicitly set
        if self.target is None or self.getPid() is None:
            self.setTarget()
            self.setProcess()

    def getDescription(self, obj, option = None):
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


    def getCommandResult(self, data, add_to_history = False, out_handle = None):
        res = lldb.SBCommandReturnObject()
        cmd = data.replace('\n', ' ').replace('\r', '')

        if out_handle is not None:
            # redirect stdout to *FILE
            f = open(out_handle, "w")
        else:
            # else default to stdout for output
            f = sys.__stdout__

        self.dbg.SetOutputFileHandle(f, True)
        handle = self.dbg.GetOutputFileHandle()
        handle_cmd = self.ci.HandleCommand(cmd, res, add_to_history)

        # keep target/process up to date
        self.syncSession(res)

<<<<<<< HEAD
        #resolve_cmd = self.ci.ResolveCommand(cmd, res)
        #print('handle command: %s'% handle_cmd)
        #print('resolvecommand: %s'% resolve_cmd)
        #print('echo cmds: %s'% lldb.SBCommandInterpreterRunOptions().GetEchoCommands())

        # write to redirected file


=======
        # TODO send separately for consumption by client UIs
>>>>>>> feature/native-lldb
        if self.processState() is not None:
            print('process: %s'% self.getDescription(self.target.GetProcess()))
            print('thread: %s'% self.getDescription(self.process.GetSelectedThread()))
            print('frame: %s'% self.getDescription(self.getSelectedFrame()))

        print('IsValid: ', res.IsValid())
        print('HasResult: ', res.HasResult())
        #print('GetErrorSize: ', res.GetErrorSize())
        #print('GetStatus: ', res.GetStatus())
        # status: 5 - exited, 2 when stopped with 2 breakpoints

        #if res.HasResult():
            # breakpoint, stepping, launched process, r
            # no need for display. vim will handle
            # add frame info to 
            #print('result: ', res.GetOutput())
            #res.PutOutput(handle)

        #else:
            # no result - help, error, exec set, stepping?
            # except when check output for prompt
            #print('no result: ', res.GetOutput())
            #res.PutOutput(handle)

        res.PutOutput(handle)


        # Vim cb gets errors in prompt

        return res

    def getSelectedFrame(self):
        frame = None
        if self.processState() is not None:
            for thread in self.process:
                frame = thread.GetSelectedFrame()

        return frame

    def getLineEntryFromFrame(self):
        """ return full path from frame """
        frame = self.getSelectedFrame()
        path = frame.GetPCAddress().GetLineEntry()
        return path

    def getBreakpointAtFileLine(self, data):
        args = parseArgs(data)
        filename = args[1]
        line_nr = args[2]
        self.getAllBreakpoints()

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
* respawn on error or user request
* define arg flags (e.g., '-internal', ...)

Start LLDB interpreter in IO loop to take commands from input prompt
and pass to debugger instance
"""
def startIOLoop(outcb, errcb):
    dbg = LLDB()
    dbg.start()
    flag_internal = '-internal'
    flag_tty = '-tty'
    tty_out = None

    while True:
        data = input("(lldb) ")


        if len(data) < 1:
            continue

        """ -tty out_handle sets output of CI """
        if flag_tty in data:
            p = compile(r'(?<=-tty)\s*([\w\\\/\.\_\-]*)')
            out = search(p, data)
            tty_out = out.group().strip() if len(out.group()) else None
            # remove -tty flag and file path from data before further processing
            p = compile(r'-tty\s*[\w\\\/\.\_\-]*')
            data = p.sub('', data)

        """ -internal commands skip LLDB's CI """
        if flag_internal in data:
            removeLastNLines(1)

            data.replace(flag_internal, '')
            if 'bp_sync' in str(data):
                outcb('breakpoint updated', dbg.getBreakpointDict())
            elif 'frame_path' in str(data):
                outcb('current file', dbg.getLineEntryFromFrame())
            elif 'clear' in str(data):
                clear()
            elif 'wipe' in str(data):
                continue


        else:
            res = dbg.getCommandResult(data, add_to_history = True, out_handle = tty_out)

            if res.Succeeded():
                output = res.GetOutput()
                outcb(output)
            else:
                output = res.GetError()
                errcb(output)

    dbg.Terminate()



<<<<<<< HEAD
=======


>>>>>>> feature/native-lldb
# start LLDB interpreter if LLDB was imported
if not lldbImported:
    print('\033]51;["call","Lldbapi_%s", ["%s"]]\007' %
            ('LldbErrFatalCb', 'Failed to import vim-lldb. Try setting g:lldb_python_interpreter_path=\'path/to/python\' in .vimrc. See README for help.',))
    sys.exit()
else:
    startIOLoop(vimOutCb, vimErrCb)

