"""T6 (plan C11, C4(f)): one adapter decision with the silent index fallbacks turned into errors.

V3 runs this on a G1 state with exactly the adapter arguments of the replay
(D2 prints them as REPLAY_ARGS; use the same RW_* environment, PYTHONPATH and
working directory = the frozen root):

  python -B diagnostics/sdmpc_n31_20260924/tests/t6_guarded_decision.py <record.json> -- <adapter args...>

How: the guards wrap hooks that configure_runtime installs (zoned segment_vsl,
the lane-profile patch), so they are entered right after configure_runtime
returns. runtime_setup.configure_runtime is wrapped before the adapter's main()
imports it (AD:12955 imports it at call time) and the guards stay active until
main() returns. The adapter module is imported, not run as __main__; its tangent
workers are separate processes (sdmpc_tangent_worker.py) and are NOT guarded:
T3 (test_n31_parity.py) covers the worker side.

The record says: whether the guards were entered, every guard error (also the
ones a decision fallback may have swallowed), how many times the 21-cell
joint_owner_neighbors.build_current_freeway_domain ran (AD path must be 0), the
full cfg FD and lane row counts right after configure_runtime (T6 record: FD 31
after LPR:436, lanes as the full cfg keeps them) and the adapter's exit status.
passed = entered and no guard error and zero domain calls and exit 0.
Exit code: 0 passed, 1 adapter failed, 2 guard/spy violation, 3 usage.
"""
from __future__ import annotations

import contextlib
import importlib
import json
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for extra in (HERE, ROOT):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

SCHEMA = 'sdmpc31-t6-guarded-decision/v1'
ADAPTER = 'evaluation.controllers.vissim_stackelberg_adapter'


def _rows(table):
    return {str(road): len(rows) for road, rows in (table or {}).items()}


def run(record_path, argv, *, target=ADAPTER):
    """Run target.main() with argv under the guards; write the record; return the exit code."""
    from evaluation.controllers import runtime_setup
    import n31_guards
    record = {'schema': SCHEMA, 'target': target, 'argv': list(argv), 'guards_entered': False,
              'build_current_freeway_domain_calls': 0, 'guard_errors': []}
    stack = contextlib.ExitStack()
    original = runtime_setup.configure_runtime

    def guarded_configure(adapter, cfg, *args, **kwargs):
        out = original(adapter, cfg, *args, **kwargs)
        if record['guards_entered']:
            raise RuntimeError('configure_runtime ran twice in one T6 decision')
        net = cfg.network
        record['full_cfg_fd_rows'] = _rows(getattr(net, 'freeway_segment_params', None))
        record['full_cfg_lane_rows'] = _rows(getattr(net, 'freeway_segment_lanes', None))
        record['lane_plant_enabled'] = bool(getattr(net, 'lane_plant_enabled', False))
        stack.enter_context(n31_guards.strict_index_guards(record))
        record['guards_entered'] = True
        return out

    runtime_setup.configure_runtime = guarded_configure
    saved_argv = sys.argv
    status = 0
    try:
        module = importlib.import_module(target)
        sys.argv = [str(getattr(module, '__file__', target)), *argv]
        module.main()
    except SystemExit as exc:
        status = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    except BaseException as exc:  # noqa: BLE001 - recorded, then reported by the exit code
        status = 1
        record['error'] = '%s: %s' % (type(exc).__name__, exc)
        record['traceback'] = traceback.format_exc()[-8000:]
    finally:
        sys.argv = saved_argv
        stack.close()
        runtime_setup.configure_runtime = original
    record['exit_status'] = status
    record['passed'] = bool(record['guards_entered'] and not record['guard_errors']
                            and record['build_current_freeway_domain_calls'] == 0 and status == 0)
    Path(record_path).write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if record['passed']:
        return 0
    return 1 if status and not record['guard_errors'] and not record['build_current_freeway_domain_calls'] else 2


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[1] != '--':
        print('usage: t6_guarded_decision.py <record.json> -- <adapter args...>', file=sys.stderr)
        return 3
    code = run(argv[0], argv[2:])
    print('N31_T6 %s record=%s' % ('PASS' if code == 0 else 'FAIL(%d)' % code, argv[0]))
    return code


if __name__ == '__main__':
    sys.exit(main())
