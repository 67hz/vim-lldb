import os
import sys

lldb_executable = 'lldb'

# is LLDB set in environ ?
if 'LLDB' in os.environ and os.path.exists(os.environ['LLDB']):
    lldb_executable = os.environ['LLDB']

# get '{lldb_executable} -P' output path and append to system path
def update_sys_path():
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
            #print("DEBUG sys.path: %s"% sys.path)
            return True;

    except CalledProcessError:
        # cannot run 'lldb -P' to get location of lldb py module
        pass

    return False
