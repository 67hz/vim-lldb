#include <fstream>
#include <memory>
#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>

#include <string>

#include "vim-lldb.h"

#if defined (__APPLE__)
#include <LLDB/LLDB.h>
#else
#include "lldb/API/SBDebugger.h"
#include "lldb/API/SBCommandInterpreterRunOptions.h"
#endif

using namespace lldb;
using namespace vim_lldb;


int Vim::setTTY(int fd, const char *p) {
  std::FILE *fp;

  if (fd == 0) {
    fp = std::fopen(p, "r");
    if (fp == NULL)
      return -1;
    this->_tty_in.emplace(fp);
  }
  else if (fd == 1) {
    fp = std::fopen(p, "w");
    if (fp == NULL)
      return -1;
    this->_tty_out.emplace(fp);
  }
  else {
    return -1;
  }

  return 1;
};

llvm::Optional<std::FILE*> Vim::getTTYIN() const {
    return this->_tty_in;
}

llvm::Optional<std::FILE*> Vim::getTTYOUT() const {
    return this->_tty_out;
}


class LLDBSentry {
  public:
    LLDBSentry() {
      SBDebugger::Initialize();
    }
    ~LLDBSentry() {
      SBDebugger::Terminate();
    }
};


int main(int argc, char** argv) {

  Vim vim;
  int c;

  // set input, output, error
  while((c = getopt(argc, argv, "i:o:e:")) != -1) {
    switch(c)
    {
      case 'i':
        vim.setTTY(0, optarg);
        break;
      case 'o':
        vim.setTTY(1, optarg);
        break;
      case 'e':
        //vim.setTTY(2, optarg);
        break;
      case '?':
        std::cout << "usage: vim-lldb -i inputfile -o outputfile -e errorfile\n";
        return 1;
      default:
        break;
    }
  }

  // set up debugger options
  LLDBSentry sentry;
  SBDebugger::Initialize();
  SBDebugger debugger(SBDebugger::Create());

  debugger.SetAsync(false);
  if (!debugger.IsValid()) {
    std::cerr << "could not create a valid debugger,\n";
    exit(EXIT_FAILURE);
  }

  if (vim.getTTYIN().hasValue()) {
    debugger.SetInputFileHandle(vim.getTTYIN().getValue(), true);
  }
  if (vim.getTTYOUT().hasValue()) {
    debugger.SetOutputFileHandle(vim.getTTYOUT().getValue(), true);
  }

  debugger.SetAsync(true);
  SBCommandInterpreterRunOptions options;
  options.SetSpawnThread(false);

  options.SetPrintResults(true);
  options.SetEchoCommands(true);
  options.SetAutoHandleEvents(true);

  options.SetStopOnContinue(false);
  options.SetStopOnError(false);
  options.SetStopOnCrash(false);
  options.SetAddToHistory(true);

  debugger.RunCommandInterpreter(options);

}

