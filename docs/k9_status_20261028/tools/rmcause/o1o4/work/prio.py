# -*- coding: utf-8 -*-
"""Set this process to BELOW_NORMAL and verify (read-only helper)."""
import ctypes, sys
from ctypes import wintypes

def below_normal():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetPriorityClass.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    k.SetPriorityClass.restype = wintypes.BOOL
    k.GetPriorityClass.argtypes = (wintypes.HANDLE,)
    k.GetPriorityClass.restype = wintypes.DWORD
    h = k.GetCurrentProcess()
    ok = k.SetPriorityClass(h, 0x4000)
    cls = k.GetPriorityClass(h)
    if not ok or cls != 0x4000:
        sys.stderr.write('priority set failed: ok=%s class=%s\n' % (ok, hex(cls)))
        raise SystemExit(3)
    return cls
