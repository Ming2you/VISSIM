"""Reuse one previously audited service ceiling after the SC1 supply repair.

No new fit or production change. Canonical fixed-command harness is preserved,
with the existing SC101 candidate installed after baseline initialization checks.
"""
from pathlib import Path
from types import SimpleNamespace
import copy, hashlib, importlib.util, json, sys

HERE = Path(__file__).resolve().parent
H = HERE.parent
ROOT = HERE.parents[3]
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def main():
    assert not (HERE / 'plan.json').exists(), 'Do not replace an existing experiment'
    evidence_path = H / 'service_ceiling/assessment.json'
    evidence = read(evidence_path)
    rebased = []
    for path, old_hash in evidence['source_pins'].items():
        current_hash = sha(Path(path))
        if current_hash == old_hash:
            continue
        assert Path(path) == ROOT / 'evaluation/controllers/head_service_resources.py'
        assert old_hash == '02beff0d7935abfe73aa129fb9fe56ef855c9ba7913399c8fce38ef2a7c58f66'
        assert current_hash == '445e384c8a9fd0a07ce651237ca5cd905c4556d061297311e2df7072e4b35271'
        rebased.append(dict(path=path, before=old_hash, after=current_hash,
            reason='Known SC1 regular alias service integration and SC109 optional physical head support; common baseline already uses this implementation. SC101 unique head and consumer checks are rerun.'))
        evidence['source_pins'][path] = current_hash
    assert len(rebased) == 1
    evidence['reuse_receipt'] = dict(original=str(evidence_path), original_sha256=sha(evidence_path),
        changed_pins=rebased, observation_rows_unchanged=True, fit_repeated=False)
    save('service_evidence.json', evidence)
    candidate_source = H / 'service_ceiling/candidate.py'
    candidate_code = candidate_source.read_text(encoding='utf8')
    assert candidate_code.count("read(HERE/'assessment.json')") == 1
    candidate_code = candidate_code.replace("read(HERE/'assessment.json')", "read(HERE/'service_evidence.json')")
    (HERE / 'candidate.py').write_text(candidate_code, encoding='utf8')
    save('preparation_failure_preserved.json', dict(stage='initial compatibility preflight', predictions_started=0,
        reason='Original service audit guarded an older head_service_resources.py. Failed before any forecast; all58other input pins unchanged.',
        resolution=rebased))
    source = H / 'connector_lane/forecast.py'
    code = source.read_text(encoding='utf8')
    replacements = {
        "tuning = HERE / 'config.json'": "tuning = H / 'connector_lane/config.json'",
        "choices=['connector_lane'], default='connector_lane'": "choices=['sc101_recombined'], default='sc101_recombined'",
        "            save('network.json', vars(cfg.network))": """            from diagnostics.repin_v3c3_review_20261001.urban_rm269.sc101_recombined.candidate import install as service
            save('candidate_application.json', service(cfg, args.at))
            save('network.json', vars(cfg.network))""",
        "    adapter.main = wrapped_main\n    v.main()": """    adapter.main = wrapped_main
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.lateral_turnover.candidate import install as turnover
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.lane_transfer_binding.probe import install as binding
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.spatial_receiving.candidate import install as receiving
    turnover()
    rows = binding()
    initial = receiving(read(H / 'spatial_receiving/plan.json')['wave_m_s'])
    v.main()
    save('ramp_receipts.json', dict(rows=rows, initial=initial))""",
        "scope='Same sc1_supply initial state and fixed actual commands. Finite connector storage then actual68 admission before route choice. Connecting-lane access uses the already pinned past-only rate; no new fit or multiplier. No native or optimizer run.'": "scope='Spatial receiving diagnostic plus previously audited SC101 straight service ceiling after SC1 supply repair. Same state, fixed actual commands, receiving constraints,450s horizon. No new fit, native, optimizer, or production change.'",
    }
    for old, new in replacements.items():
        assert code.count(old) == 1, old
        code = code.replace(old, new)
    (HERE / 'forecast.py').write_text(code, encoding='utf8')
    compile(code, str(HERE / 'forecast.py'), 'exec')

    loader = importlib.util.spec_from_file_location('audited_sc101', HERE / 'candidate.py')
    candidate = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(candidate)
    checks = []
    for at in (2400, 3300):
        path = H / 'connector_lane' / f'forecast{at}' / 'network.json'
        before = read(path)
        cfg = SimpleNamespace(network=SimpleNamespace(**copy.deepcopy(before)))
        receipt = candidate.install(cfg, at)
        after = vars(cfg.network)
        changed = [k for k in after if after[k] != before[k]]
        assert changed == ['movement_capacity_by_movement_veh_h']
        a, b = after[changed[0]], before[changed[0]]
        assert [k for k in a if a[k] != b[k]] == [candidate.MOVEMENT]
        assert after['local_service_pool'] == before['local_service_pool']
        assert after['known_legsplit_routes'] == before['known_legsplit_routes']
        checks.append(dict(at=at, baseline=str(path), changed_fields=changed, receipt=receipt))
    assert checks[0]['receipt']['after_veh_h'] == checks[1]['receipt']['after_veh_h']
    paths = [Path(__file__), HERE / 'forecast.py', HERE / 'candidate.py', HERE / 'service_evidence.json', source, H / 'connector_lane/config.json',
             H / 'service_ceiling/candidate.py', H / 'service_ceiling/assessment.json',
             H / 'service_ceiling/tests.log', H / 'spatial_receiving/plan.json',
             H.parent / 'urban260/verify.py']
    pins = dict(read(H / 'spatial_receiving/plan.json')['source_pins'])
    pins.update({str(p.resolve()): sha(p) for p in paths})
    for p, digest in pins.items():
        assert sha(Path(p)) == digest, p
    save('preflight.json', dict(status='passed', network_checks=checks,
        prior_service_tests_reused=7, baseline_setup_assertions_retained=True,
        production_changed=False, fits=0))
    save('plan.json', dict(status='prepared', source_pins=pins,
        hypothesis='SC1 corrected supply is now cut by the old SC101 service ceiling; previously tested ceiling and supply fix were not combined.',
        budget=dict(fixed450=2, conditional_fresh150=1, new_fits=0, full_ad=0, full_sdmpc=0, native=0),
        condition_for_3300='Run the reserved150 only if paired head errors materially improve with conservation and feasible existing caps. Otherwise stop.',
        success='Improve physical discharge and meaningful joint cost response. Local count improvement alone is not gain qualification.',
        failed_candidate_policy='No capacity grid, added timing fit, or automatic native launch.',
        previous_source='service_ceiling: past1650-1950 queued-prefix head evidence; reuse5236.479 unchanged',
        unchanged=['network', 'demand', 'Omega701', '450s decision horizon', 'terminalOFF', 'commands', 'receivers', 'current route/lane tags'],
        production_changed=False))
    print(json.dumps(dict(status='prepared', checks=checks, pins=len(pins)), ensure_ascii=False))


if __name__ == '__main__':
    main()
