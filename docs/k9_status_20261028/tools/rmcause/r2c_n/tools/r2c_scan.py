r"""R2c step 1 (pre-declared, PRE_R2C.md): stage-1 scan of the two 10681-only rule-RM arms, one at a time.
Same functions and pins as O1 o1_scan.py (stage1_scan.scan -> stage1_uninserted.reconstruct_from_scan).
find_rule_policy -> the arm's OWN prepared/rule_policy.json only (zone_dsds only; never a sibling glob).
FZP lock: <r2c_n>/fzp.lock is created exclusively before the first FZP read and deleted at the end (retry every 30 s).
Writes only <r2c_n>/scans/r1_s<S>/ and <r2c_n>/out/r2c_scan_log.json.  Run folders are read only.
Usage: python -B r2c_scan.py [--run 31=run_retry1] [--run 41=...]
       (both seeds; default output folder 'run'; --run names a relaunch folder of that seed, PRE_R2C sec.8;
        refuses if a run is not completed)"""
import hashlib, io, json, os, sys, time, ctypes, datetime
from ctypes import wintypes
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
R2C = os.path.dirname(HERE)
LOCK = os.path.join(R2C, 'fzp.lock')
STAGE1 = r'D:\VISSIM-merge\tools\stage1'
STAGE1_SHA = {
    'stage1_common.py': 'e000c69eebad2636c00299727ceb1624d408d5ac3c6ae26204301b1fa891fdae',
    'stage1_scan.py': '651c4f51fdddf49d46c77ed4c28b0626c410b3282426b9fd30f2a6ef43f7625f',
    'stage1_uninserted.py': '19eba94ed01bce47b591b47362aba13b2ac697cfbf2cb9156954b573e7727cd1',
    'stage1_report.py': 'cb4ccc3a431f32ebb6f716a0b67c148a71d82470c443b4851f80832d98d7a1b9',
}
ROOT = r'D:\VISSIM_runs\20261001_v3c3'
NET_SHA = {31: '046303541667838f30045a06d230fb5b31944a18db483770539dfcc873176f0d',
           41: 'e4953eaf8c8f983f28b9a14c684075757ddd45e180e63f2235dc9db8b4ed7524'}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def below_normal():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.SetPriorityClass.restype = wintypes.BOOL
    k.GetPriorityClass.argtypes = [wintypes.HANDLE]
    k.GetPriorityClass.restype = wintypes.DWORD
    h = k.GetCurrentProcess()
    k.SetPriorityClass(h, 0x00004000)
    return k.GetPriorityClass(h)


def take_lock(max_wait_sec=6 * 3600):
    t0 = time.time()
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, ('r2c_scan pid=%d at=%s\n' % (os.getpid(), datetime.datetime.now().astimezone().isoformat())).encode())
            os.close(fd)
            return round(time.time() - t0, 1)
        except FileExistsError:
            if time.time() - t0 > max_wait_sec:
                raise SystemExit('FZP lock busy for %d s: %s' % (max_wait_sec, LOCK))
            time.sleep(30)


def main():
    prio = below_normal()
    for n, want in STAGE1_SHA.items():
        if sha(os.path.join(STAGE1, n)) != want:
            raise SystemExit('stage1 tool %s sha mismatch' % n)
    sys.path.insert(0, STAGE1)
    import stage1_common as C
    import stage1_scan as S
    import stage1_uninserted as U

    def own_policy(run_dir):
        p = os.path.join(os.path.dirname(os.path.abspath(run_dir)), 'prepared', 'rule_policy.json')
        return p if os.path.exists(p) else None
    C.find_rule_policy = own_policy
    sub = {31: 'run', 41: 'run'}
    args = sys.argv[1:]
    while args:
        if args[0] != '--run' or len(args) < 2 or '=' not in args[1]:
            raise SystemExit('usage: r2c_scan.py [--run <seed>=<folder>] ...')
        k, v = args[1].split('=', 1)
        if int(k) not in sub or not v.startswith('run') or os.sep in v or '/' in v:
            raise SystemExit('bad --run %s' % args[1])
        sub[int(k)] = v
        args = args[2:]
    infos = {}
    for s in (31, 41):
        rd = os.path.join(ROOT, 's%d_v3c3rm10681' % s, sub[s])
        info = C.run_files(rd)
        info['tag'] = 'r1_s%d' % s
        if not C.run_completed(info):
            raise SystemExit('r1 s%d not completed' % s)
        for k in ('fzp', 'inpx', 'err'):
            if not info.get(k) or not os.path.exists(info[k]):
                raise SystemExit('r1_s%d: %s missing' % (s, k))
        if sha(info['inpx']) != NET_SHA[s]:
            raise SystemExit('r1_s%d network sha differs from the rm arm' % s)
        infos[s] = info
    waited = take_lock()
    log = {'priority': hex(prio), 'lock': LOCK, 'lock_wait_sec': waited, 'runs': []}
    try:
        for s, info in infos.items():
            dest = os.path.join(R2C, 'scans', 'r1_s%d' % s)
            os.makedirs(dest, exist_ok=True)
            t1 = time.time()
            out, net = S.scan(info, force=False)
            out['an'] = {'tag': info['tag'], 'source_run_dir': info['run_dir'], 'driver': os.path.abspath(__file__),
                         'driver_sha256': sha(os.path.abspath(__file__)), 'tool_sha256': STAGE1_SHA,
                         'priority_class': hex(prio), 'find_rule_policy': 'own arm prepared/rule_policy.json only',
                         'shim': None, 'inpx_sha256': sha(info['inpx']), 'err_sha256': sha(info['err']),
                         'fzp_bytes': os.path.getsize(info['fzp'])}
            C.jdump(out, os.path.join(dest, 'scan.json'))
            un = U.reconstruct_from_scan(out, net)
            C.jdump(un, os.path.join(dest, 'uninserted.json'), indent=1)
            rec = {'tag': info['tag'], 'seed': out['seed'], 'rows': out['rows'], 'frames': out['frames'],
                   'scan_sec': round(out['scan_sec'], 1), 'wall_sec': round(time.time() - t1, 1), 'dest': dest,
                   'zone_policy_match': out['speed']['zone_policy_match'],
                   'scan_sha256': sha(os.path.join(dest, 'scan.json')),
                   'un_sha256': sha(os.path.join(dest, 'uninserted.json'))}
            log['runs'].append(rec)
            print(json.dumps(rec), flush=True)
    finally:
        os.remove(LOCK)
    os.makedirs(os.path.join(R2C, 'out'), exist_ok=True)
    with io.open(os.path.join(R2C, 'out', 'r2c_scan_log.json'), 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=1)
    print('done')


if __name__ == '__main__':
    main()
