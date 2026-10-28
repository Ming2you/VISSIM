# test_vsl_launcher.py - dry-run scenarios for vsl_launcher.ps1 (no WMI, no VISSIM, no kill). 2026-10-27 KST.
# Each scenario runs the launcher in -Mode dryrun on a fresh root under VS/dryrun/<name>/root and checks the
# markers / end records / log lines it leaves. Usage: python -B test_vsl_launcher.py  (prints PASS/FAIL per scenario)
import glob, json, os, shutil, subprocess, sys

VS = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/vsl_v3c3'
L = VS + '/tools/vsl_launcher.ps1'
D = VS + '/dryrun'


def rj(vissim=True, finished=False, completed=None, error=None):
    d = {'cscript_pid': 4242, 'cscript_start': '2026-10-27T10:00:00.0000000+09:00', 'completed': False, 'error': error}
    if vissim:
        d['vissim'] = {'pid': 5151, 'start': '2026-10-27T10:00:05.0000000+09:00'}
    if finished:
        d['finished'] = '2026-10-27T12:00:00.0000000+09:00'
        d['completed'] = bool(completed)
    return json.dumps(d)


def W(path, text):
    return {'path': path, 'text': text}


OK_DISK = {'C': 24, 'D': 222}
SC = {
    'A_normal_seats': ([
        {'vissim': 2, 'disk': OK_DISK, 'note': 'two other VISSIM; launch s31'},
        {'vissim': 2, 'write': [W('s31/run/run.json', rj())], 'note': 's31 VISSIM up -> 3; launch s41'},
        {'vissim': 2, 'note': 's41 pending -> 3+1 = 4; wait'},
        {'vissim': 2, 'write': [W('s41/run/run.json', rj())], 'note': 's41 up -> 4; wait'},
        {'vissim': 1, 'note': 'one other ended -> 3; launch s43'},
        {'vissim': 1, 'write': [W('s43/run/run.json', rj()), W('s31/run/run.json', rj(finished=True, completed=True)),
                                W('s41/run/run.json', rj(finished=True, completed=True))], 'note': 's31 s41 done'},
        {'vissim': 1, 'write': [W('s43/run/run.json', rj(finished=True, completed=True))], 'note': 's43 done -> exit'},
        {'vissim': 1, 'note': 'should not be reached'},
    ], {'launched': ['s31_run1', 's41_run1', 's43_run1'], 'end': {'s31_run1': 'done', 's41_run1': 'done', 's43_run1': 'done'},
        'stopped': False, 'log_has': ['SEAT_WAIT s43_run1 vissim=3 pending=1', 'SEAT_WAIT s43_run1 vissim=4 pending=0', 'EXIT nothing active'],
        'log_not': ['should not be reached']}),
    'B_stall_retry_once': ([
        {'vissim': 0, 'disk': OK_DISK, 'note': 'launch s31'},
        {'vissim': 0, 'write': [W('s31/run/run.json', rj())], 'note': 'launch s41'},
        {'vissim': 0, 'write': [W('s41/run/run.json', rj())], 'note': 'launch s43'},
        {'vissim': 0, 'write': [W('s43/run/run.json', rj()),
                                W('s41/run/run.json', rj(finished=True, completed=False, error='Progress300s: complete native FZP timestamp stopped advancing'))],
         'note': 's41 stalled (runner killed own PIDs) -> relaunch once into run_retry1'},
        {'vissim': 0, 'write': [W('s41/run_retry1/run.json', rj()), W('s31/run/run.json', rj(finished=True, completed=True)),
                                W('s43/run/run.json', rj(finished=True, completed=True))], 'note': 's31 s43 done'},
        {'vissim': 0, 'write': [W('s41/run_retry1/run.json', rj(finished=True, completed=True))], 'note': 'retry done -> exit'},
        {'vissim': 0, 'note': 'should not be reached'},
    ], {'launched': ['s31_run1', 's41_run1', 's41_run2', 's43_run1'],
        'end': {'s31_run1': 'done', 's41_run1': 'stalled', 's41_run2': 'done', 's43_run1': 'done'}, 'stopped': False,
        'log_has': ['LAUNCH s41_run2', 'EXIT nothing active'], 'log_not': ['should not be reached'],
        'cmd_has': {'s41_run2': '-Output %ROOT%\\s41\\run_retry1 -Execute -MinimumFreeGiB 8 -AllowConcurrent > %ROOT%\\s41\\launch_retry1.log 2>&1'}}),
    'C_abnormal_stops': ([
        {'vissim': 3, 'disk': OK_DISK, 'note': 'launch s31 (3 others)'},
        {'vissim': 3, 'write': [W('s31/run/run.json', rj())], 'note': '4 -> wait'},
        {'vissim': 3, 'write': [W('s31/run/run.json', rj(finished=True, completed=False, error='Fixed-profile native LDP/readback validation failed'))],
         'note': 's31 abnormal -> stop launching -> exit'},
        {'vissim': 0, 'note': 'should not be reached'},
    ], {'launched': ['s31_run1'], 'end': {'s31_run1': 'abnormal'}, 'stopped': True,
        'log_has': ['LAUNCH_STOPPED abnormal_end s31_run1', 'EXIT nothing active'], 'log_not': ['should not be reached', 'LAUNCH s41']}),
    'D_disk_low': ([
        {'vissim': 0, 'disk': {'C': 24, 'D': 7.5}, 'note': 'D below 8 GB'},
        {'vissim': 0, 'note': 'should not be reached'},
    ], {'launched': [], 'end': {}, 'stopped': True, 'log_has': ['LAUNCH_STOPPED disk_low'], 'log_not': ['should not be reached']}),
    'F_backstop_kill_then_retry': ([
        {'vissim': 0, 'disk': OK_DISK, 'note': 'launch s31'},
        {'vissim': 2, 'write': [W('s31/run/run.json', rj())], 'stall_age_sec': {'s31_run1': 700},
         'note': 's31 no progress 700 s while runner alive -> backstop kills own PIDs only; launch s41 (2+1 = 3)'},
        {'vissim': 2, 'write': [W('s31/run/run.json', rj(finished=True, completed=False, error=None)), W('s41/run/run.json', rj())],
         'note': 'runner ended after the kill -> stalled -> s31 retry (seat 2+1 = 3 < 4)'},
        {'vissim': 2, 'write': [W('s31/run_retry1/run.json', rj())], 'note': 's31 retry up (2+2 = 4) -> s43 waits'},
        {'vissim': 0, 'note': 'others ended -> launch s43'},
        {'vissim': 0, 'write': [W('s31/run_retry1/run.json', rj(finished=True, completed=True)), W('s41/run/run.json', rj(finished=True, completed=True)),
                                W('s43/run/run.json', rj(finished=True, completed=True))], 'note': 'all done'},
        {'vissim': 0, 'note': 'should not be reached'},
    ], {'launched': ['s31_run1', 's31_run2', 's41_run1', 's43_run1'],
        'end': {'s31_run1': 'stalled', 's31_run2': 'done', 's41_run1': 'done', 's43_run1': 'done'}, 'stopped': False,
        'log_has': ['STALL_BACKSTOP s31_run1', 'killed own PIDs only: cscript:4242:dryrun,vissim:5151:dryrun', 'SEAT_WAIT s43_run1 vissim=4 pending=0',
                    'DRYRUN_SUMMARY wmi_creates=4 kills=s31_run1:cscript:4242,s31_run1:vissim:5151'],
        'log_not': ['should not be reached']}),
    'G_second_stall_stops': ([
        {'vissim': 3, 'disk': OK_DISK, 'note': 'launch s31'},
        {'vissim': 3, 'write': [W('s31/run/run.json', rj(finished=True, completed=False, error='Startup300s: no complete FZP data timestamp showing actual native progression'))],
         'note': 's31 startup stall -> retry'},
        {'vissim': 3, 'write': [W('s31/run_retry1/run.json', rj(finished=True, completed=False, error='Progress300s: complete native FZP timestamp stopped advancing'))],
         'note': 'retry stalled again -> stop'},
        {'vissim': 3, 'note': 'should not be reached'},
    ], {'launched': ['s31_run1', 's31_run2'], 'end': {'s31_run1': 'stalled', 's31_run2': 'stalled'}, 'stopped': True,
        'log_has': ['LAUNCH_STOPPED stalled_again s31_run2'], 'log_not': ['should not be reached', 'LAUNCH s41']}),
    'H_stop_file': ([
        {'vissim': 0, 'disk': OK_DISK, 'write': [W('STOP_VSL_LAUNCHER', 'stop')], 'note': 'stop file'},
        {'vissim': 0, 'note': 'should not be reached'},
    ], {'launched': [], 'end': {}, 'stopped': True, 'log_has': ['LAUNCH_STOPPED stop_file'], 'log_not': ['should not be reached']}),
    'I_sha_change': ([
        {'vissim': 0, 'disk': OK_DISK, 'sha_bad': True, 'note': 'fixed file changed'},
        {'vissim': 0, 'note': 'should not be reached'},
    ], {'launched': [], 'end': {}, 'stopped': True, 'log_has': ['LAUNCH_STOPPED fixed_file_changed'], 'log_not': ['should not be reached']}),
}
# E: restart - first launcher launches s31 and ends (scenario exhausted, s31 active); second launcher must not relaunch s31
E1 = [{'vissim': 0, 'disk': OK_DISK, 'note': 'launch s31'}]
E2 = [{'vissim': 0, 'disk': OK_DISK, 'write': [W('s31/run/run.json', rj())], 'note': 'restart: s31 active, launch s41 only'},
      {'vissim': 0, 'write': [W('s41/run/run.json', rj())], 'note': 'launch s43'}]


def run(name, steps, root, log):
    sp = os.path.join(D, name, 'scenario_%d.json' % len(glob.glob(os.path.join(D, name, 'scenario_*.json'))))
    json.dump({'steps': steps}, open(sp, 'w', encoding='utf-8'))
    p = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', L.replace('/', '\\'), '-Mode', 'dryrun',
                        '-Root', root, '-Log', log, '-Scenario', sp.replace('/', '\\'), '-PollSec', '0'], capture_output=True, text=True)
    return p


def state(root):
    ld = os.path.join(root, '_launcher')
    launched = sorted(os.path.basename(f)[9:-5] for f in glob.glob(os.path.join(ld, 'launched_*.json')))
    end = {os.path.basename(f)[4:-5]: json.load(open(f, encoding='utf-8-sig'))['status'] for f in glob.glob(os.path.join(ld, 'end_*.json'))}
    rc = {os.path.basename(f)[8:-5]: json.load(open(f, encoding='utf-8-sig')) for f in glob.glob(os.path.join(ld, 'receipt_*.json'))}
    return launched, end, os.path.exists(os.path.join(ld, 'LAUNCH_STOPPED.json')), rc


def main():
    if os.path.exists(D):
        shutil.rmtree(D)
    allok = True
    out = {}
    for name, (steps, exp) in SC.items():
        os.makedirs(os.path.join(D, name), exist_ok=True)
        root = (D + '/' + name + '/root').replace('/', '\\')
        log = (D + '/' + name + '/launcher.log').replace('/', '\\')
        p = run(name, steps, root, log)
        launched, end, stopped, rc = state(root)
        text = open(log, encoding='utf-8').read() if os.path.exists(log) else ''
        errs = []
        if p.returncode != 0:
            errs.append('exit %d %s' % (p.returncode, p.stderr[-800:]))
        if launched != sorted(exp['launched']):
            errs.append('launched %s' % launched)
        if end != exp['end']:
            errs.append('end %s' % end)
        if stopped != exp['stopped']:
            errs.append('stopped %s' % stopped)
        for s in exp.get('log_has', []):
            if s not in text:
                errs.append('log lacks: ' + s)
        for s in exp.get('log_not', []):
            if s in text:
                errs.append('log has: ' + s)
        for k, s in exp.get('cmd_has', {}).items():
            if s.replace('%ROOT%', root) not in rc.get(k, {}).get('cmdline', ''):
                errs.append('cmdline %s' % k)
        wl = os.path.join(root, 'wmi_launch_lines_vsl.txt')
        n_lines = len(open(wl, encoding='utf-8').read().splitlines()) if os.path.exists(wl) else 0
        if n_lines != len(exp['launched']):
            errs.append('wmi lines %d' % n_lines)
        ok = not errs
        allok &= ok
        out[name] = {'ok': ok, 'errs': errs}
        print(('PASS ' if ok else 'FAIL ') + name, '; '.join(errs))
    # E restart
    name = 'E_restart_no_double_launch'
    os.makedirs(os.path.join(D, name), exist_ok=True)
    root = (D + '/' + name + '/root').replace('/', '\\')
    log = (D + '/' + name + '/launcher.log').replace('/', '\\')
    p1 = run(name, E1, root, log)
    p2 = run(name, E2, root, log)
    launched, end, stopped, rc = state(root)
    text = open(log, encoding='utf-8').read()
    wl = open(os.path.join(root, 'wmi_launch_lines_vsl.txt'), encoding='utf-8').read().splitlines()
    errs = []
    if p1.returncode or p2.returncode:
        errs.append('exit %d %d' % (p1.returncode, p2.returncode))
    if launched != ['s31_run1', 's41_run1', 's43_run1']:
        errs.append('launched %s' % launched)
    if sum(1 for x in wl if '  s31_run1  ' in x) != 1:
        errs.append('s31 launched more than once')
    if text.count('START sha256=') != 2:
        errs.append('two starts expected')
    ok = not errs
    allok &= ok
    out[name] = {'ok': ok, 'errs': errs}
    print(('PASS ' if ok else 'FAIL ') + name, '; '.join(errs))
    json.dump({'all_ok': allok, 'scenarios': out}, open(os.path.join(D, 'test_result.json'), 'w', encoding='utf-8'), indent=1)
    print('ALL_OK', allok)
    sys.exit(0 if allok else 1)


if __name__ == '__main__':
    main()
