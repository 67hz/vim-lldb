import os
import sys
import vim


lldb_executable = 'lldb'

# is LLDB set in environ ?
if 'LLDB' in os.environ and os.path.exists(os.environ['LLDB']):
    lldb_executable = os.environ['LLDB']

# vimrc g:lldb_path overrides above environ variable
vimrc_lldb_path = vim.eval('g:lldb_custom_path')
if vimrc_lldb_path != "":
    lldb_executable = vimrc_lldb_path

# get '{lldb_executable} -P' output path and append to system path
def get_lldb_path():
    from subprocess import check_output, CalledProcessError
    try:
        with open(os.devnull, 'w') as fnull:
            lldb_minus_p_path = check_output(
                "%s -P" %
                lldb_executable,
                shell=True,
                stderr=fnull).strip().decode("utf-8")

        if not os.path.exists(lldb_minus_p_path):
            pass
        else:
            sys.path[0:0] = [lldb_minus_p_path]
            print(sys.path)
            return True;

    except CalledProcessError:
        # cannot run 'lldb -P' to get location of lldb py module
        pass

    return False


get_lldb_path()
