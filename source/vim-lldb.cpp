#include <stdlib.h>
#include <getopt.h>
#include <lldb/API/SBDefines.h>
#include <lldb/lldb-defines.h>

#include "vim-lldb.h"

#if defined (__APPLE__)
#include <lldb/LLDB>
#else
#include "lldb/API/SBDebugger.h"
#include "lldb/API/SBCommandInterpreterRunOptions.h"
#endif

using namespace lldb;


std::string EscapeString(const std::string& message, void *data) {
  // see (vim) :h term_api for job->vim communication
  std::string vim_escape_seq = R"(\033]51;["call","Lldbapi_LldbOutCb", [{}, {}]]\007')";
  return vim_escape_seq;
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

int main(int argc, char* argv[])
{
  /*
   * need to pass in pty data from vim: as args and use internal method for modifying
   */

  LLDBSentry sentry;
  SBDebugger::Initialize();
  SBDebugger debugger(SBDebugger::Create());

  if (!debugger.IsValid()) {
    std::cerr << "could not create a valid debugger,\n";
    exit(EXIT_FAILURE);
  }

  SBCommandInterpreterRunOptions options;

  debugger.RunCommandInterpreter(options);



}

