r"""O1 step 1: stage-1 scan of the two v3c3 rule-RM arms (s31_v3c3rm, s41_v3c3rm), one at a time.
Same functions as V-A va_scan.py (stage1_scan.scan -> stage1_uninserted.reconstruct_from_scan), sha-pinned stage-1 tools.
No FZP shim (the fast_nc runner FZP has no 0.10 s row, like NC3).  find_rule_policy -> the arm's OWN prepared policy only
(never a sibling glob: s37 is sealed).  Writes only to o1o4/o1/scans/rm_s<S>/.  Run folders read only."""
import hashlib, io, json, os, sys, time, ctypes
from ctypes import wintypes
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
O1 = os.path.dirname(HERE)
STAGE1 = r'D:\VISSIM-merge\tools\stage1'
STAGE1_SHA = {
    'stage1_common.py': 'e000c69eebad2636c00299727ceb1624d408d5ac3c6ae26204301b1fa891fdae',
    'stage1_scan.py': '651c4f51fdddf49d46c77ed4c28b0626c410b3282426b9fd30f2a6ef43f7625f',
    'stage1_uninserted.py': '19eba94ed01bce47b591b47362aba13b2ac697cfbf2cb9156954b573e7727cd1',
    'stage1_report.py': 'cb4ccc3a431f32ebb6f716a0b67c148a71d82470c443b4851f80832d98d7a1b9',
}
ROOT = r'D:\VISSIM_runs\20261001_v3c3'


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
    log = {'priority': hex(prio), 'runs': []}
    for s in (31, 41):
        rd = os.path.join(ROOT, 's%d_v3c3rm' % s, 'run')
        info = C.run_files(rd)
        info['tag'] = 'rm_s%d' % s
        if not C.run_completed(info):
            raise SystemExit('RM s%d not completed' % s)
        for k in ('fzp', 'inpx', 'err'):
            if not info.get(k) or not os.path.exists(info[k]):
                raise SystemExit('rm_s%d: %s missing' % (s, k))
        dest = os.path.join(O1, 'scans', 'rm_s%d' % s)
        os.makedirs(dest, exist_ok=True)
        t1 = time.time()
        out, net = S.scan(info, force=False)
        out['an'] = {'tag': info['tag'], 'source_run_dir': rd, 'driver': os.path.abspath(__file__),
                     'tool_sha256': STAGE1_SHA, 'priority_class': hex(prio),
                     'find_rule_policy': 'own arm prepared/rule_policy.json only',
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
    with io.open(os.path.join(O1, 'out', 'o1_scan_log.json'), 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=1)
    print('done')


if __name__ == '__main__':
    main()
