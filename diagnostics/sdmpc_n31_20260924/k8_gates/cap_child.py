"""Adapter process for K8 captures: run the adapter as `python adapter.py ...` until sdmpc.solve builds its
surrogate Query (sdmpc.py:579), store that request template, stop. (termcost tc_capture pattern.)

    python -B cap_child.py <out_dir> <variant> <adapter.py> <adapter args...>

variant: base | s5 | s9 | s59   -- scratch patch of build_local_observation_summary in the adapter module
  s5 : storage stopped share = (observed stopped - ready queue)/storage for contiguous|stopped_instant links
       (85e D4 rule, without its hard ProjectionError; violations are counted instead)
  s9 : storage speed weight = moving vehicles (instant count - stopped; <0.5 -> no sample) when moving_only is on
Nothing under the code root is edited; the patch is compiled from the file text into the running module only.
Also records the projection activation numbers (same rules, computed from the function's own locals).
Started by capture.py (k8common.base_env); the code root is the adapter's parents[2].
s5 applies to every contiguous|stopped_instant link, link 127 included (K8_REVIEW B7: K8-4 covers 127 too).
"""
import hashlib
import json
import os
import pickle
import runpy
import sys
import time
from collections import defaultdict
from pathlib import Path

if len(sys.argv) < 4 or sys.argv[1] in ('-h', '--help'):
    print(__doc__)
    raise SystemExit(0 if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help') else 2)
OUT = Path(sys.argv[1]); VARIANT = sys.argv[2]; ADAPTER = sys.argv[3]; ARGS = sys.argv[4:]
OUT.mkdir(parents=True, exist_ok=True)
STARTED = time.perf_counter()
REC = {'variant': VARIANT}


class Captured(BaseException):
    pass


S5_OLD_A = "        queue_count = max(0.0, count - storage_count)\n"
S5_NEW_A = (S5_OLD_A +
            "        _k8_obs_stopped = min(float(count), max(0.0, float(link_stopped_counts.get(str(link), 0.0))))\n"
            "        _k8_res = _k8_obs_stopped / count if count > 0.0 else 0.0\n"
            "        if queue_source_by_link.get(str(link)) in ('contiguous', 'stopped_instant') and str(link) in link_stopped_counts:\n"
            "            if queue_count > _k8_obs_stopped + 1e-8:\n"
            "                _K8_DIAG['ready_exceeds_stopped'] = _K8_DIAG.get('ready_exceeds_stopped', 0) + 1\n"
            "            _k8_res = min(1.0, max(0.0, _k8_obs_stopped - queue_count) / storage_count) if storage_count > 0.0 else 0.0\n")
S5_OLD_B = "                    stopped_share = min(1.0, max(0.0, float(link_stopped_counts.get(str(link), 0.0)) / count))\n"
S5_NEW_B = "                    stopped_share = _k8_res\n"
S9_OLD = ("            for storage_link in storage_links:\n"
          "                speed_weight_by_storage[storage_link] = (\n"
          "                    speed_weight_by_storage.get(storage_link, 0.0) + float(count)\n"
          "                )\n"
          "                speed_moment_by_storage[storage_link] = (\n"
          "                    speed_moment_by_storage.get(storage_link, 0.0)\n"
          "                    + float(count) * observed_kph\n"
          "                )\n")
S9_NEW = ("            _k8_w = float(count)\n"
          "            if _moving_speed_enabled():\n"
          "                _k8_loc = _mapping(state_json.get('local_observation'))\n"
          "                _k8_w = max(0.0, _as_float(_mapping(_k8_loc.get('link_counts')).get(str(link)), 0.0)\n"
          "                            - _as_float(_mapping(_k8_loc.get('link_stopped_counts')).get(str(link)), 0.0))\n"
          "                if _k8_w < 0.5:\n"
          "                    _k8_w = 0.0\n"
          "            for storage_link in storage_links:\n"
          "                speed_weight_by_storage[storage_link] = speed_weight_by_storage.get(storage_link, 0.0) + _k8_w\n"
          "                speed_moment_by_storage[storage_link] = speed_moment_by_storage.get(storage_link, 0.0) + _k8_w * observed_kph\n")


def patched_source():
    text = Path(ADAPTER).read_text(encoding='utf-8')
    start = text.index('\ndef build_local_observation_summary(') + 1
    end = text.index('\ndef ', start + 10) + 1
    src = text[start:end]
    if VARIANT in ('s5', 's59'):
        for old, new in ((S5_OLD_A, S5_NEW_A), (S5_OLD_B, S5_NEW_B)):
            if src.count(old) != 1:
                raise RuntimeError('S5 anchor not unique')
            src = src.replace(old, new)
    if VARIANT in ('s9', 's59'):
        if src.count(S9_OLD) != 1:
            raise RuntimeError('S9 anchor not unique')
        src = src.replace(S9_OLD, S9_NEW)
    first_line = text[:start].count('\n') + 1
    return '\n' * (first_line - 1) + src, src


def projection_record(frame):
    loc = frame.f_locals
    sj = loc.get('state_json') or {}
    local = sj.get('local_observation') or {}
    inst_counts = local.get('link_counts') or {}
    inst_stopped = local.get('link_stopped_counts') or {}
    link_counts = loc.get('link_counts') or {}
    stopped = loc.get('link_stopped_counts') or {}
    qsrc = loc.get('queue_source_by_link') or {}
    qcount = loc.get('queue_count_by_link') or {}
    scount = loc.get('storage_count_by_link') or {}
    slinks = loc.get('storage_links_by_link') or {}
    rec = {'moving_speed_enabled': bool((loc.get('_moving_speed_diag') or {}).get('enabled'))}
    orig_st = fixed_st = viol = viol_veh = 0.0
    by_src = defaultdict(float)
    n_links = 0
    for link, count in link_counts.items():
        link = str(link)
        c = float(count)
        n = float(scount.get(link, 0.0))
        if c <= 0.0 or n <= 0.0 or not slinks.get(link):
            continue
        s = min(c, max(0.0, float(stopped.get(link, 0.0))))
        q = float(qcount.get(link, 0.0))
        o = n * min(1.0, s / c)
        src = qsrc.get(link)
        f = o
        if src in ('contiguous', 'stopped_instant') and link in stopped:
            if q > s + 1e-8:
                viol += 1
                viol_veh += q - s
            f = min(n, max(0.0, s - q))
        if abs(o - f) > 1e-9:
            n_links += 1
        orig_st += o
        fixed_st += f
        by_src[str(src)] += o - f
    rec.update(S5_storage_stopped_orig_veh=orig_st, S5_storage_stopped_fixed_veh=fixed_st,
               S5_shift_105_to_15_veh=orig_st - fixed_st, S5_links_changed=n_links, S5_shift_by_source=dict(by_src),
               S5_ready_exceeds_stopped_links=viol, S5_ready_exceeds_stopped_veh=viol_veh,
               queue_source_hist={k: sum(1 for v in qsrc.values() if v == k) for k in set(qsrc.values())},
               storage_occupancy_total_veh=float(sum((loc.get('urban_link_storage_occupancy') or {}).values())),
               storage_stopped_total_veh=float(sum((loc.get('urban_link_storage_stopped') or {}).values())),
               storage_count_total_veh=float(sum(scount.values())), queue_count_total_veh=float(sum(qcount.values())))
    w = dict(loc.get('speed_weight_by_storage') or {})
    m = dict(loc.get('speed_moment_by_storage') or {})
    speeds = loc.get('link_speeds_kph') or {}
    fw, fm = dict(w), dict(m)
    changed = all_stopped_links = 0
    for link, count in link_counts.items():
        link = str(link)
        c = float(count)
        sl = slinks.get(link) or []
        if c <= 0.0 or link not in speeds or not sl:
            continue
        v = float(speeds[link])
        wm = max(0.0, float(inst_counts.get(link, 0.0) or 0.0) - float(inst_stopped.get(link, 0.0) or 0.0))
        if wm < 0.5:
            wm = 0.0
            all_stopped_links += 1
        if wm != c:
            changed += 1
        for s_ in sl:
            fw[s_] = fw.get(s_, 0.0) - c + wm
            fm[s_] = fm.get(s_, 0.0) - c * v + wm * v
    orig = {k: m[k] / x for k, x in w.items() if x > 1e-9}
    fixed = {k: fm[k] / x for k, x in fw.items() if x > 1e-9}
    rows = sorted(((fixed[k] - orig[k], k, orig[k], fixed[k]) for k in orig if k in fixed), key=lambda t: -abs(t[0]))
    rec.update(S9_storages_observed=len(orig), S9_links_weight_changed=changed, S9_links_all_stopped=all_stopped_links,
               S9_storages_changed_gt1pct=sum(1 for d, k, o, f in rows if abs(d) > 0.01 * max(o, 1e-9)),
               S9_storages_to_nominal=[k for k in orig if k not in fixed],
               S9_mean_abs_delta_kph=(sum(abs(r[0]) for r in rows) / len(rows)) if rows else 0.0,
               S9_top=[[k, round(o, 2), round(f, 2)] for d, k, o, f in rows[:15]],
               S9_speed_orig=orig, S9_speed_fixed=fixed)
    return rec


def prof(frame, event, arg):
    if event == 'call' and frame.f_code.co_name == 'main' and frame.f_code.co_filename == str(Path(ADAPTER)) \
            and 'K8_PATCHED' not in REC:
        REC['K8_PATCHED'] = VARIANT
        if VARIANT != 'base':
            g = frame.f_globals
            padded, src = patched_source()
            g['_K8_DIAG'] = {}
            exec(compile(padded, ADAPTER, 'exec'), g)
            REC['patched_sha256'] = hashlib.sha256(src.encode('utf-8')).hexdigest()
    if event == 'return' and frame.f_code.co_name == 'build_local_observation_summary':
        try:
            REC['projection'] = projection_record(frame)
            REC['diag'] = dict(frame.f_globals.get('_K8_DIAG', {}))
        except Exception as exc:
            REC['projection_error'] = repr(exc)
        sys.setprofile(None)


def hooked(self, template, check_budget, emit, runner=None):
    tbytes = pickle.dumps(template, protocol=5)
    follower, state, reference, _ = template['owned']
    (OUT / 'template.pickle').write_bytes(tbytes)
    meta = dict(schema='k8-capture/v1', variant=VARIANT, sim_sec=float(state.time_sec), horizon=template['horizon'],
                axes=len(template['axes']), costs_order=list(template['costs_order']),
                template_sha256=hashlib.sha256(tbytes).hexdigest(),
                python_hash_seed=os.environ.get('PYTHONHASHSEED'), capture_wall_sec=time.perf_counter() - STARTED)
    REC['meta'] = meta
    (OUT / 'capture.json').write_text(json.dumps(REC, indent=1, default=str), encoding='utf-8')
    REC['captured'] = True
    raise Captured()


sys.path[0] = str(Path(ADAPTER).resolve().parent)
root = Path(ADAPTER).resolve().parents[2]
sys.path.insert(1, str(root))
import importlib.abc  # noqa: E402


class Post(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname != 'evaluation.controllers.sdmpc_tangent_surrogate':
            return None
        idx = sys.meta_path.index(self)
        for f in sys.meta_path[idx + 1:]:
            fs = getattr(f, 'find_spec', None)
            spec = fs(fullname, path, target) if fs else None
            if spec is not None:
                break
        else:
            return None
        orig = spec.loader.exec_module

        def exec_module(module):
            orig(module)
            module.Query.__init__ = hooked
        spec.loader.exec_module = exec_module
        return spec


sys.meta_path.insert(0, Post())
sys.argv = [ADAPTER] + ARGS
sys.setprofile(prof)
code = 3
try:
    runpy.run_path(ADAPTER, run_name='__main__')
    print('CAPTURE_FAILED adapter returned', flush=True)
    code = 2
except Captured:
    print('CAPTURE_OK', flush=True)
    code = 0
except SystemExit as e:
    if REC.get('captured'):
        print('CAPTURE_OK', flush=True)
        code = 0
    else:
        print('CAPTURE_FAILED exit', e.code, flush=True)
        code = 3
if 'captured' not in REC:
    (OUT / 'capture_failed.json').write_text(json.dumps(REC, indent=1, default=str), encoding='utf-8')
sys.stdout.flush(); sys.stderr.flush()
os._exit(code)
