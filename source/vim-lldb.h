#ifndef VIM_LLDB_H
#define VIM_LLDB_H

#include <iostream>
#include <vector>
#include <lldb/API/SBDebugger.h>

namespace vim_lldb {

  class Vim {
    public:
      // Vim escape sequence to trap output. see :h term_sendkeys
      Vim() = default;
      ~Vim() = default;

      bool setIOEscapeSequence(const std::string& sequence);
      const std::string& getIOEscapeSequence() const;

      // IO to Vim terminals
      int setTTY(int fd, const char *p);
      std::FILE* getTTYIN() const;
      std::FILE* getTTYOUT() const;

      ssize_t write(const std::string& message, const void *data);
      ssize_t read(const std::string& message) const;
    private:
      std::string _io_escape_seq;
      std::FILE *_tty_in;
      std::FILE *_tty_out;
  };




} // end vim_lldb namespace

#endif // ifndef VIM_LLDB_H
