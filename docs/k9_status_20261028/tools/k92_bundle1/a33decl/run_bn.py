"""Run one command at BELOW_NORMAL priority (Declare A33 helper; the child inherits the priority class).
    python -B run_bn.py <program> [args...]   -> exit code of the child; env PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1"""
import ctypes
import os
import subprocess
import sys

sys.dont_write_bytecode = True
ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)
env = dict(os.environ, PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1')
sys.exit(subprocess.run(sys.argv[1:], env=env).returncode if len(sys.argv) > 1 else 2)
