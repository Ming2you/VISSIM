"""Install the explicitly approved single replacement; no forecast or native call."""
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
REL = Path('diagnostics/sdmpc_n31_20260924/integration_20260926')
OLD = SOURCE / REL / 'native_vsl_multizone2250'
NEW = SOURCE / REL / 'native_vsl_multizone2250_repaired_20261016'
OLD_RT = Path('D:/VISSIM_runtime/20261015_vsl_multizone2250')
RT = Path('D:/VISSIM_runtime/20261016_vsl_multizone2250_repaired')
RESULTS = Path('D:/VISSIM_runs/20261016_vsl_multizone2250_repaired_s29')
FIXED = HERE / 'command_metadata_repair/selected/commands'

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def save(p, v):
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def rows(p):
    with Path(p).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def main():
    for p in (NEW, RT, RESULTS, HERE/'replacement_preparation_20261016.json'):
        assert not p.exists(), f'Existing preparation/attempt preserved: {p}'
    assert not (SOURCE/'STOP').exists()
    plan = read(HERE/'plan.json')
    assert plan['next_stage']['native_launches'] == 1
    assert plan['next_stage']['status'] == 'native_failed_at2250_no_retry'
    proof = read(HERE/'metadata_repair_verification.json')
    assert proof['fixed_rows'] == 639 and proof['fixed_invalid_rows'] == 0
    assert proof['metadata_matches_validated_baseline_all_rows']
    protocol = read(OLD/'protocol.json')
    assert protocol['arms'] == ['selected'] and protocol['start_sec'] == 2250 and protocol['end_sec'] == 2700
    # Verify all original evidence before changing destinations or copying anything.
    for p, digest in protocol['command_pins'].items():
        assert sha(p) == digest, f'Original evidence changed: {p}'
    repaired_checks = []
    baseline_commands = Path(protocol['controlled_prefix']['commands'][0]['csv']['source']).parent
    for sec in (2250, 2400, 2550):
        a = rows(OLD/f'selected/commands/action_{sec:06d}.csv')
        b = rows(FIXED/f'action_{sec:06d}.csv')
        baseline = rows(baseline_commands/f'action_{sec:06d}.csv')
        assert len(a) == len(b) == len(baseline) == 213
        for old, new, valid in zip(a, b, baseline):
            assert {k:v for k,v in old.items() if k != 'metadata'} == {k:v for k,v in new.items() if k != 'metadata'}
            assert new['metadata'] == valid['metadata']
            assert {'offset_writer=experiment','physical_signal_contract=1','offset_experiment=1'} <= set(new['metadata'].split(';'))
        repaired_checks.append({'sec':sec, 'csv_sha256':sha(FIXED/f'action_{sec:06d}.csv'), 'rows':213, 'actuators_identical_to_failed_preparation':True})
    # A new packet preserves every byte of the failed packet and prior frozen tree.
    dest = NEW/'selected/commands'
    dest.mkdir(parents=True)
    RT.mkdir(parents=True)
    for sec in [1]+list(range(150, 2700, 150)):
        for suffix in ('json','csv'):
            p = FIXED/f'action_{sec:06d}.{suffix}'
            shutil.copyfile(p, dest/p.name)
            assert sha(p) == sha(dest/p.name)
    terminal = read(dest/'action_002550.json')
    terminal['metadata']['sim_sec'] = 2700
    terminal['metadata']['terminal_no_future_traffic'] = True
    save(dest/'action_002700.json', terminal)
    shutil.copyfile(dest/'action_002550.csv', dest/'action_002700.csv')
    pins = {}
    for raw, digest in protocol['command_pins'].items():
        p = Path(raw)
        if p.is_relative_to(OLD):
            p = NEW / p.relative_to(OLD)
            digest = sha(p)
        pins[str(p)] = digest
    for p in (Path(__file__), HERE/'metadata_repair_verification.json', HERE/'writer_metadata_check2250/writer_metadata_verification.json'):
        pins[str(p)] = sha(p)
    for entry in protocol['controlled_prefix']['commands']:
        for suffix in ('json','csv'):
            record = entry[suffix]
            record['destination'] = str(NEW / Path(record['destination']).relative_to(OLD))
            assert sha(record['destination']) == record['sha256'] == sha(record['source'])
    protocol['command_pins'] = pins
    protocol['authorization'] = '2026-10-16 explicit user: 수정본으로 1회 추가 실행; one replacement attempt, no automatic retry'
    protocol['replacement_of_failed_protocol'] = {'path':str(OLD/'protocol.json'), 'sha256':sha(OLD/'protocol.json'), 'failure_sec':2250, 'failed_results_preserved':True}
    protocol['metadata_repair'] = {'proof':str(HERE/'metadata_repair_verification.json'), 'sha256':sha(HERE/'metadata_repair_verification.json'), 'checks':repaired_checks}
    save(NEW/'protocol.json', protocol)
    wrapper = (OLD_RT/'run_prepared_selected.ps1').read_text(encoding='utf-8-sig')
    assert sha(OLD_RT/'run_prepared_selected.ps1') == 'f609f446ccf0d3ef71f9eb3f74b4a8cac8f4f62647ceb8f29697cce10aad1012'
    wrapper = wrapper.replace('D:/VISSIM_runs/20261015_vsl_multizone2250_s29', str(RESULTS).replace('\\','/'))
    wrapper = wrapper.replace('native_vsl_multizone2250', NEW.name)
    (RT/'run_prepared_selected.ps1').write_text(wrapper, encoding='utf-8')
    now = datetime.now(timezone.utc).isoformat()
    receipt = {'status':'replacement_installed_pending_preflight', 'authorized_utc':now, 'authorization':'수정본으로 1회 추가 실행', 'source':str(SOURCE), 'protocol':str(NEW/'protocol.json'), 'protocol_sha256':sha(NEW/'protocol.json'), 'runtime':str(RT), 'results':str(RESULTS), 'wrapper':str(RT/'run_prepared_selected.ps1'), 'wrapper_sha256':sha(RT/'run_prepared_selected.ps1'), 'new_native_budget':1, 'retries':0, 'new_forecasts':0, 'old_attempt_preserved':True, 'repaired_checks':repaired_checks}
    save(HERE/'replacement_preparation_20261016.json', receipt)
    save(RT/'preparation_receipt.json', receipt)
    save(HERE/'plan_before_replacement_20261016.json', plan)
    plan.setdefault('native_attempt_history', []).append(plan['next_stage'])
    plan['next_stage'] = {'status':'replacement_prepared_pending_preflight', 'native_budget':1, 'retries':0, 'native_runtime':str(RT), 'native_results':str(RESULTS), 'native_source':str(SOURCE), 'prepared_native_protocol':str(NEW/'protocol.json'), 'installed_protocol':str(NEW/'protocol.json'), 'installed_protocol_sha256':sha(NEW/'protocol.json'), 'preflight_started':0, 'preflight_verified':False, 'freeze_count':0, 'freeze_verified':False, 'frozen_tree':None, 'native_launches':0, 'preparation_receipt':str(HERE/'replacement_preparation_20261016.json'), 'wrapper_preparation':str(RT/'preparation_receipt.json'), 'matched_forecasts_completed':3, 'matched_forecasts_summary':str(HERE/'matched_off2250_v3/summary.json'), 'postprocess':{'status':'requires_normal2700_and_all_owner_closure', 'reuse_existing_analyzer_and_baseline_cache':True}, 'updated_utc':now}
    plan['status'] = 'authorized_replacement_prepared'
    plan['next'] = 'Run canonical preflight once, freeze once, and dispatch the repaired selected arm once. Retain old failed attempt. Reuse completed forecasts. No retries.'
    plan['updated_utc'] = now
    plan['additional_native_authorization'] = {'user_text':'수정본으로 1회 추가 실행', 'date':'2026-10-16', 'additional_attempts':1, 'automatic_retries':0, 'prior_attempts':1}
    plan['offline_vsl_transport_audit']['replacement_native_authorization'] = 'explicit human approval received2026-10-16; one additional native attempt only'
    save(HERE/'plan.json', plan)
    print(json.dumps(receipt, ensure_ascii=False))

if __name__ == '__main__':
    main()
