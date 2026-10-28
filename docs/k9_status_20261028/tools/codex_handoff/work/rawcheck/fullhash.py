import hashlib, os, time, ctypes
try: ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception: pass
LOCK = "C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/omega/fzp.lock"
F = {"nc_raw": "D:/VISSIM_handoff/20261024/raw/nc/vissim_eval/sdmpc31_nc9000_s29_001.fzp",
     "lnc": "D:/VISSIM_runs/vsl_repro_s29/none/run/vissim_eval/vsl_seed29_none_001.fzp"}
for k, p in F.items():
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, f"rawcheck fullhash {p}\n".encode()); os.close(fd); break
        except FileExistsError: time.sleep(5)
    try:
        h = hashlib.sha256(); n = 0
        with open(p, "rb") as fh:
            for raw in fh:
                if raw[:1].isdigit():
                    h.update(raw.rstrip(b"\r\n") + b"\n"); n += 1
        print(k, "data rows", n, "sha256 LF all data rows (0-9000)", h.hexdigest())
    finally:
        os.remove(LOCK)
