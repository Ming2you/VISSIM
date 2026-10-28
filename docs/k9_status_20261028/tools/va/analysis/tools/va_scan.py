r"""V-A analysis step 1 (amendment 34 sec.8.0, 8.1): stage-1 scan of the three V-A runs.
python -B va_scan.py --profile va|selftest  ->  <profile scans>/va_s<S>/{scan.json, uninserted.json}, <out>/va_scan_log.json
Same functions as J1 an_scan.py (stage1_scan.scan -> stage1_uninserted.reconstruct_from_scan), find_rule_policy -> None,
runner FZP 0.10 s row skipped by a read-only shim (no time cut).  J1 / NC3 scans are reused after the sha256 prefix
check of amendment 34 sec.8.1; a mismatching one is rescanned here with the same functions and flagged.
Tools sha-pinned. BELOW_NORMAL. One run at a time. Writes nothing into run folders."""
import io
import json
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import va_common as V  # noqa: E402


class _Skip(object):
    def __init__(self, f, skip, stats):
        self._f, self._skip, self._s = f, skip, stats

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self._f.close()

    def __iter__(self):
        for raw in self._f:
            if self._skip and raw.startswith(self._skip):
                self._s['skipped'] += 1
                continue
            yield raw


class _IoShim(object):
    def __init__(self, target, skip):
        self.target, self.skip = os.path.normcase(os.path.abspath(target)), skip
        self.stats = {'skipped': 0}

    def open(self, path, mode='r', *a, **kw):
        if 'b' not in mode or any(c in mode for c in 'wax+'):
            raise SystemExit('shim: unexpected mode %r' % mode)
        f = io.open(path, mode, *a, **kw)
        if os.path.normcase(os.path.abspath(path)) == self.target and self.skip:
            return _Skip(f, self.skip, self.stats)
        return f


def runner_info(run, seed, tag):
    return {'run_dir': run['run_dir'], 'arm_dir': os.path.dirname(run['run_dir']), 'tag': tag,
            'run_json': {'completed': True, 'exit_code': 0, 'seed': seed,
                         'source': 'built by hand (runner has no run.json); validity per the V-A validity stage'},
            'fzp': run['fzp'], 'inpx': run['inpx'], 'err': run['err'], 'analysis_dir': None}


def do_scan(C, S, U, info, skip, dest, prio):
    for k in ('fzp', 'inpx', 'err'):
        if not info.get(k) or not os.path.exists(info[k]):
            raise SystemExit('%s: %s missing' % (info['tag'], k))
    os.makedirs(dest, exist_ok=True)
    shim = _IoShim(info['fzp'], skip)
    real = S.io
    S.io = shim
    t1 = time.time()
    try:
        out, net = S.scan(info, force=False)
    finally:
        S.io = real
    out['an'] = {'tag': info['tag'], 'source_run_dir': info['run_dir'], 'driver': os.path.abspath(__file__),
                 'tool_sha256': V.STAGE1_SHA, 'priority_class': hex(prio), 'find_rule_policy': 'disabled (None)',
                 'shim': {'skip_prefix': skip.decode() if skip else None, 'skipped_rows': shim.stats['skipped']},
                 'inpx_sha256': V.sha(info['inpx']), 'err_sha256': V.sha(info['err'])}
    C.jdump(out, os.path.join(dest, 'scan.json'))
    un = U.reconstruct_from_scan(out, net)
    C.jdump(un, os.path.join(dest, 'uninserted.json'), indent=1)
    return {'tag': info['tag'], 'seed': out['seed'], 'rows': out['rows'], 'frames': out['frames'],
            'skipped_rows': shim.stats['skipped'], 'scan_sec': round(out['scan_sec'], 1),
            'wall_sec': round(time.time() - t1, 1), 'dest': dest}


def main():
    prof = V.profile_from_argv()
    pin = V.require_pinned(prof, __file__)
    t0 = time.time()
    prio = V.set_below_normal()
    C = V.import_stage1()
    import stage1_scan as S
    import stage1_uninserted as U
    log = {'profile': prof.name, 'pinned': pin, 'priority': hex(prio), 'runs': [], 'reused': {}, 'rescanned': []}
    # J1 / NC3: reuse after the sha16 check, else rescan (disclosed)
    for tag in sorted(V.J1_SCAN_SHA16):
        d, ok = V.j1_scan_dir(prof, tag)
        log['reused'][tag] = {'dir': d, 'sha16_ok': ok}
        if ok:
            continue
        seed = int(tag[-2:])
        if tag.startswith('j1_'):
            info, skip = runner_info(V.j1_run(seed), seed, tag), V.FZP_SKIP
        else:
            info, skip = C.run_files(V.nc3_run(seed)['run_dir']), None
            info['tag'] = tag
            if not C.run_completed(info):
                raise SystemExit('NC3 s%d not completed' % seed)
        rec = do_scan(C, S, U, info, skip, d, prio)
        log['rescanned'].append(rec)
        print('RESCANNED', json.dumps(rec), flush=True)
    for seed in V.SEEDS:
        tag = 'va_s%d' % seed
        rec = do_scan(C, S, U, runner_info(prof.va_run(seed), seed, tag), V.FZP_SKIP,
                      os.path.join(prof.scans, tag), prio)
        log['runs'].append(rec)
        print(json.dumps(rec), flush=True)
    log['elapsed_sec'] = round(time.time() - t0, 1)
    V.jdump(log, os.path.join(prof.out, 'va_scan_log.json'))
    print('done %.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
