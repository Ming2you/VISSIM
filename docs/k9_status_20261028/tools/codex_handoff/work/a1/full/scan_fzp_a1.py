# RAW_CHECK own FZP scanner (not codex code). Read-only on FZP. One file per call; shared lock with other agents.
# Residence: per-frame link counts, trapezoid from empty network at t=0, last frame (<=8100) held to 8100.
# Also: prefix (rows <= 895.1) sha256 of LF-normalised data lines, full sha (rows <= 8100), per-vehicle first/last seen.
import sys, os, time, json, hashlib, collections, ctypes
import numpy as np
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL
except Exception:
    pass
SMOKE = "--smoke" in sys.argv  # A1 copy: --smoke maps "a1" to the codex joint FZP and writes to scan_smoke
OUT = "C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/a1/full/" + ("scan_smoke" if SMOKE else "scan")
LOCK = "C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/omega/fzp.lock"
R = "D:/VISSIM_handoff/20261024/raw"
RUNS = {
    "nc": f"{R}/nc/vissim_eval/sdmpc31_nc9000_s29_001.fzp",
    "joint": f"{R}/joint/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp",
    "window": f"{R}/window/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp",
    "off": f"{R}/off/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp",
    "freeway_only": f"{R}/freeway_only/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp",
    "urban_only": f"{R}/urban_only/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp",
    "lnc": "D:/VISSIM_runs/vsl_repro_s29/none/run/vissim_eval/vsl_seed29_none_001.fzp",
    "a1": f"{R}/joint/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp" if SMOKE else "D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp",
}
END = 8100.0
PREFIX_END = 895.1
name = sys.argv[1]
F = RUNS[name]
os.makedirs(OUT, exist_ok=True)
# lock
while True:
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"rawcheck pid={os.getpid()} file={F} start={time.strftime('%Y-%m-%d %H:%M:%S')}\n".encode())
        os.close(fd)
        break
    except FileExistsError:
        time.sleep(5)
try:
    st0 = os.stat(F)
    t0 = time.time()
    area = collections.defaultdict(float)
    prev_t, prev = 0.0, {}
    cur_t, cur = None, collections.Counter()
    rows = rows_le_end = frames = 0
    hp = hashlib.sha256(); hfull = hashlib.sha256(); prows = 0
    first = {}   # no -> (t, link, pos, speed)
    last = {}    # no -> (t, link)
    tmax = None
    done_area = False
    def commit(t, counts):
        global prev_t, prev, frames
        dt = t - prev_t
        for k in set(prev) | set(counts):
            area[k] += (prev.get(k, 0) + counts.get(k, 0)) * dt / 2 / 3600
        prev_t, prev = t, dict(counts)
        frames += 1
    with open(F, "rb") as fh:
        for raw in fh:
            if not raw[:1].isdigit():
                continue
            p = raw.split(b";", 7)
            t = float(p[0]); no = int(p[1]); link = int(p[2])
            rows += 1
            tmax = t
            if no not in first:
                first[no] = (t, link, float(p[4]), float(p[6]))
            last[no] = (t, link)
            if t <= PREFIX_END:
                prows += 1; hp.update(raw.rstrip(b"\r\n") + b"\n")
            if t <= END:
                rows_le_end += 1; hfull.update(raw.rstrip(b"\r\n") + b"\n")
                if cur_t is not None and t != cur_t:
                    commit(cur_t, cur); cur = collections.Counter()
                cur_t = t
                cur[link] += 1
            elif not done_area:
                commit(cur_t, cur); done_area = True
                for k, n in prev.items():
                    area[k] += n * (END - prev_t) / 3600
    if not done_area:
        commit(cur_t, cur)
        for k, n in prev.items():
            area[k] += n * (END - prev_t) / 3600
        last_frame = prev_t
    else:
        last_frame = prev_t
    st1 = os.stat(F)
    assert (st0.st_size, st0.st_mtime_ns) == (st1.st_size, st1.st_mtime_ns)
    nos = np.array(sorted(first), dtype=np.int64)
    np.savez_compressed(f"{OUT}/{name}_veh.npz", no=nos,
        t_first=np.array([first[n][0] for n in nos]), link_first=np.array([first[n][1] for n in nos], dtype=np.int64),
        pos_first=np.array([first[n][2] for n in nos]), speed_first=np.array([first[n][3] for n in nos]),
        t_last=np.array([last[n][0] for n in nos]), link_last=np.array([last[n][1] for n in nos], dtype=np.int64))
    res = dict(name=name, fzp=F, bytes=st0.st_size, rows_total=rows, rows_le_8100=rows_le_end, frames_le_8100=frames,
               last_frame_le_8100=last_frame, t_max=tmax, vehicles=len(first),
               prefix_rows_le_895_1=prows, prefix_sha256_lf=hp.hexdigest(), full_sha256_lf_le_8100=hfull.hexdigest(),
               link_residence_veh_h={str(k): v for k, v in sorted(area.items())}, scan_sec=round(time.time() - t0, 1))
    json.dump(res, open(f"{OUT}/{name}.json", "w"), indent=0)
    print(name, "rows", rows, "rows<=8100", rows_le_end, "frames", frames, "last", last_frame, "tmax", tmax, "veh", len(first),
          "prefix", prows, hp.hexdigest()[:16], "full", hfull.hexdigest()[:16], "whole", round(sum(area.values()), 6), "sec", res["scan_sec"])
finally:
    try:
        os.remove(LOCK)
    except FileNotFoundError:
        pass
