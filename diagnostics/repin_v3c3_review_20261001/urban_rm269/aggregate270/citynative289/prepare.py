"""Reuse the qualified city-only commands with canonical pinned concurrency.

No new controller, forecast, coefficients, native retry, or queue mutation.
The previous preparation's serial gate is replaced after reviewing the same
canonical concurrency path used by the completed isolated10681 experiment.
"""
import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BASE = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
OLD = BASE / 'native_urbanrm269_cityonly287_2400_r2'
NEW = BASE / 'native_urbanrm269_cityonly289_2400'
PREVIOUS = HERE.parent / 'citysplit287'
RESULTS = 'E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29'
RUNTIME = 'E:/VISSIM_runtime/20261010_urbanrm269_cityonly289'
read = lambda p: json.loads(Path(p).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def main():
    assert not NEW.exists() and not (HERE/'plan.json').exists()
    assert not Path(RESULTS).exists() and not Path(RUNTIME).exists()
    old_plan = read(PREVIOUS/'launch_plan.json')
    assert old_plan['native_dispatches'] == 0 and old_plan['preflight_passed']
    protocol = read(OLD/'protocol.json')
    assert protocol['start_sec'] == 2400 and protocol['end_sec'] == 2850
    assert protocol['seed'] == 29 and protocol['arms'] == ['selected']
    assert not protocol['native_authorization_pending']
    assert protocol['max_native_runs'] == 1 and protocol['automatic_retries'] == 0
    for path, digest in protocol['command_pins'].items():
        assert sha(path) == digest, path
    for path, digest in old_plan['source_pins'].items():
        assert sha(path) == digest, path
    assert not any((path/'STOP').exists() for path in (
        ROOT, OLD, PREVIOUS, HERE, Path(old_plan['results_root']),
        Path(old_plan['runtime']), Path('E:/VISSIM_runtime/20261008_coupling268_vsl_three'),
        Path('E:/VISSIM_runs/20261008_coupling268_off_s29_8100')))

    # Immutable commands only: do not hard-link mutable configs or status files.
    commands = NEW/'selected/commands'
    commands.mkdir(parents=True)
    receipts = []
    for source in sorted((OLD/'selected/commands').iterdir()):
        assert source.is_file() and source.suffix in ('.json', '.csv')
        target = commands/source.name
        assert target.resolve().is_relative_to(ROOT.resolve())
        os.link(source, target)
        assert sha(source) == sha(target)
        receipts.append(dict(source=str(source), destination=str(target), sha256=sha(target)))

    def remap(value):
        if isinstance(value, dict):
            return {remap(k):remap(v) for k,v in value.items()}
        if isinstance(value, list):
            return [remap(v) for v in value]
        if isinstance(value, str):
            return value.replace(str(OLD), str(NEW)).replace(OLD.as_posix(), NEW.as_posix())
        return value

    updated = remap(copy.deepcopy(protocol))
    updated['allowed_concurrent_vissim'] = [dict(pid=41468, creation_time='2026-10-09T12:06:54.723367Z')]
    updated['concurrency_note'] = 'Same city-only treatment. Preserve existing coupling268 off run by exact PID and birth; canonical runner rejects other VISSIM instances. No queue edits.'
    updated['command_pins'][str(Path(__file__))] = sha(__file__)
    save(NEW/'protocol.json', updated)
    for path,digest in updated['command_pins'].items():
        assert sha(path) == digest, path
    save(HERE/'command_reuse.json', dict(files=receipts, commands_changed=False,
        immutable_hardlinks_only=True, prefix_traffic_parity_still_requires_native_validation=True))
    post = read(PREVIOUS/'postprocess_plan.json')
    def postmap(value):
        if isinstance(value, dict): return {k:postmap(v) for k,v in value.items()}
        if isinstance(value, list): return [postmap(v) for v in value]
        if isinstance(value, str):
            return value.replace(str(OLD),str(NEW)).replace(OLD.as_posix(),NEW.as_posix()).replace(
                old_plan['results_root'],RESULTS).replace('20261010_urbanrm269_cityonly287','20261010_urbanrm269_cityonly289')
        return value
    save(HERE/'postprocess_plan.json',postmap(post))
    plan=dict(status='prepared_pending_canonical_preflight',created_utc=datetime.now(timezone.utc).isoformat(),
        protocol=str(NEW/'protocol.json'), results_root=RESULTS, runtime=RUNTIME,
        source=str(ROOT), frozen_tree=None, freeze_dispatches=0, native_dispatches=0,
        maximum_new_native_arms=1, automatic_retries=0,
        concurrent_vissim=updated['allowed_concurrent_vissim'],
        preserved_queue='E:/VISSIM_runtime/20261008_coupling268_vsl_three/queue_state.json',
        replaces_unlaunched_preparation=str(PREVIOUS/'launch_plan.json'),
        prior_concurrency_evidence=str(BASE/'native_urbanrm269_10681only_2400/protocol.json'),
        canonical_runner=str(BASE/'native_pair1200/run_pair.ps1'),
        freezer=str(ROOT/'tools/sdmpc31/freeze_worktree.ps1'),
        source_pins={str(p):sha(p) for p in (NEW/'protocol.json',Path(__file__),
            HERE/'command_reuse.json',HERE/'postprocess_plan.json',BASE/'native_pair1200/run_pair.ps1',
            ROOT/'tools/sdmpc31/freeze_worktree.ps1',ROOT/'diagnostics/sdmpc_n31_20260924/tools/freeze_manifest.py')},
        gates=['Recheck exact live reserved process, no other VISSIM, all STOPs and duplicate traces.',
            'Canonical preflight and FREEZE_DONE/FREEZE.json required; no source edits during freeze.',
            'NoGlobalKill, MaxAttempts1, startup300s and existing watchdog only.',
            'Native prefix, LDP/VSL and normal2850 plus exact owned closure required before analysis.'],
        goal_complete=False)
    save(HERE/'plan.json',plan)
    print(json.dumps(dict(status=plan['status'],commands=len(receipts),native_dispatches=0),ensure_ascii=False))


if __name__ == '__main__':
    main()
