# K9-2 bundle 1 configuration snapshot hook (K8_PREDECLARATION_AMENDMENT_24 section 4.3 G-K1 static; diagnostics only).
# Loaded only through k92_replay.py --extra-pythonpath <this folder>; inert unless env K92_CFGSNAP_DIR is set.
# sys.monitoring (Python 3.12), one tool id: PY_START of configure_runtime (runtime_setup.py) keeps its `cfg` argument;
# its PY_RETURN writes the snapshot; for SDMPC controllers the PY_RETURN of install_cost_ownership (sdmpc.py) writes the
# ownership table.  Passive: nothing of the program is called or changed; after the last snapshot file the process
# ends with os._exit(0) (no decision is made).  Files in K92_CFGSNAP_DIR:
#   network.pickle      cfg.network after configure_runtime (the object the price workers receive pickled, RS:501-531)
#   metadata.json       the configure_runtime metadata (json, default=repr)
#   ownership.json      the SDMPC cost-ownership table (SDMPC controllers only)
#   snapshot.json       argv, controller, written files
# An exception inside the hook is written to snapshot_error.txt and the process ends with os._exit(9).
import os
import sys

_OUT = os.environ.get('K92_CFGSNAP_DIR')


def _setup():
    import json
    import pickle
    import traceback

    mon = sys.monitoring
    tool = None
    for cand in (3, 4, 5, 1, 2):
        try:
            mon.use_tool_id(cand, 'k92_cfgsnap')
            tool = cand
            break
        except ValueError:
            continue
    if tool is None:
        raise RuntimeError('k92_cfgsnap: no free sys.monitoring tool id')
    os.makedirs(_OUT, exist_ok=True)
    argv = list(sys.argv)
    controller = argv[argv.index('--controller') + 1] if '--controller' in argv else None
    sdmpc_controller = controller in ('wu-link', 'pstack-flagship')
    state = {'written': [], 'cfg': None, 'ret_codes': set()}
    DISABLE = mon.DISABLE

    def fail(where):
        with open(os.path.join(_OUT, 'snapshot_error.txt'), 'a', encoding='utf-8') as h:
            h.write('%s\n%s\n' % (where, traceback.format_exc()))
        os._exit(9)

    def finish():
        with open(os.path.join(_OUT, 'snapshot.json'), 'w', encoding='utf-8') as h:
            json.dump({'argv': argv, 'controller': controller, 'written': state['written'], 'pid': os.getpid()}, h,
                      indent=1)
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            os._exit(0)

    def find_frame(code):
        f = sys._getframe(1)
        while f is not None and f.f_code is not code:
            f = f.f_back
        return f

    def on_start(code, offset):
        name, base = code.co_name, os.path.basename(code.co_filename)
        if (name, base) == ('configure_runtime', 'runtime_setup.py'):
            try:
                frame = find_frame(code)
                state['cfg'] = frame.f_locals.get('cfg') if frame is not None else None
                if code not in state['ret_codes']:
                    state['ret_codes'].add(code)
                    mon.set_local_events(tool, code, mon.events.PY_RETURN)
            except Exception:  # noqa: BLE001
                fail('configure_runtime start')
            return None
        if (name, base) == ('install_cost_ownership', 'sdmpc.py'):
            try:
                if code not in state['ret_codes']:
                    state['ret_codes'].add(code)
                    mon.set_local_events(tool, code, mon.events.PY_RETURN)
            except Exception:  # noqa: BLE001
                fail('ownership start')
            return None
        return DISABLE

    def on_return(code, offset, retval):
        name = code.co_name
        try:
            if name == 'configure_runtime':
                with open(os.path.join(_OUT, 'network.pickle'), 'wb') as h:
                    pickle.dump(state['cfg'].network, h, protocol=5)
                with open(os.path.join(_OUT, 'metadata.json'), 'w', encoding='utf-8') as h:
                    json.dump(retval[2], h, indent=1, sort_keys=True, default=repr)
                state['written'] += ['network.pickle', 'metadata.json']
                if not sdmpc_controller:
                    finish()
            elif name == 'install_cost_ownership':
                with open(os.path.join(_OUT, 'ownership.json'), 'w', encoding='utf-8') as h:
                    json.dump(retval, h, indent=1, sort_keys=True, default=repr)
                state['written'].append('ownership.json')
                finish()
        except Exception:  # noqa: BLE001
            fail('return ' + name)
        return None

    mon.register_callback(tool, mon.events.PY_START, on_start)
    mon.register_callback(tool, mon.events.PY_RETURN, on_return)
    mon.set_events(tool, mon.events.PY_START)


if _OUT:
    try:
        _setup()
    except Exception:  # noqa: BLE001
        import traceback
        with open(os.path.join(_OUT, 'snapshot_setup_error.txt'), 'a', encoding='utf-8') as _h:
            _h.write(traceback.format_exc())
        os._exit(8)
