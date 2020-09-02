from __future__ import print_function

import os
import sys
import lldb
import socket
from multiprocessing import Process, Value

import lldb_path

lldb_path.update_sys_path()

log = open('lldb_server.log', 'a')
log.write("\n\nnew run\n\n")

try:
    import lldb
except ImportError:
    #vim.command("let g:lldb_disabled=1")
    print("Unable to load vim/lldb module, vim-lldb is disabled. Check lldb is available on path with `lldb -P` and codesigned or set lldb_path in .vimrc. See README for setup help.")
    pass


HOST = ''
PORT = 65400

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
        # during step/continue do not return from function until process stops
        # async is enabled by default
        self.dbg.SetAsync(False)
        self.ci = self.dbg.GetCommandInterpreter()

        #exe = os.path.join(os.getcwd(), 'par')
        #self.dbg.CreateTarget(exe)
        self.frame = "live frame"
        #q.put("debugger: %s"% dbg)


    def terminate():
        self.dbg.Terminate()
        self.dbg = None

    def test(q, x):
        q.put(x + 1243)
        q.put("debugger: %s"% dbg)


    def getCommandResult(self, data):
        """ run cmd in ci and returns (success, output) """
        res = lldb.SBCommandReturnObject()
        cmd = data.replace('\n', ' ').replace('\r', '')
        self.ci.HandleCommand(cmd, res)
        #self.ci.HandleCommand('breakpoint set -f main.c -l %d' % 12, res)
        log.write('(lldb) res: %s'% str(res))
        return res



def startServer():
    dbg = LLDB()
    dbg.start()
    log.write('Server started')

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            while True:
                data = conn.recv(1024).decode()
                if (data == 'EOF'):
                    print('closing server')
                    break

                if not data:
                    break
                res = dbg.getCommandResult(data)
                if res.Succeeded():
                    res = res.GetOutput()
                    
                else:
                    res = res.GetError()

                conn.sendall(res.encode())
                res = ''



        s.close()



startServer()

