LLVM_CONFIG?=llvm-config

CXX=g++
BIN_DIR?=$(PWD)/bin
SRC_DIR?=$(PWD)
LDFLAGS+=$(shell $(LLVM_CONFIG) --ldflags)
COMMON_FLAGS=-Wall -Wextra
CXXFLAGS+=$(COMMON_FLAGS) $(shell $(LLVM_CONFIG) --cxxflags)
CPPFLAGS+=$(shell $(LLVM_CONFIG) --cppflags) -I$(SRC_DIR)
VIM_LLDB=vim-lldb
VIM_LLDB_OBJECTS=vim-lldb.o


default: $(VIM_LLDB)

%.o: $(SRC_DIR)/%.cpp
	@echo Compiling $*.cpp
	$(CXX) -c $(CPPFLAGS) $(CXXFLAGS) $<

$(VIM_LLDB): $(VIM_LLDB_OBJECTS)
	@echo Compiling $@
	$(CXX) -o $(BIN_DIR)/$@ $(CXXFLAGS) $(LDFLAGS) -llldb $^


clean:
	rm -f $(VIM_LLDB) $(VIM_LLDB_OBJECTS)

PHONY: .clean

