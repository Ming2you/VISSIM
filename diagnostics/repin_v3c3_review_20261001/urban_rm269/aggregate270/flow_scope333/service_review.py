"""Separate SC105 green, ready-stock and receiving limits from saved332 traces."""
from collections import Counter
from pathlib import Path
import json
import pickle
from diagnostics.validate_native_signal_record import read_ldp_frames
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.flow_scope333 import audit
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.city_loss322.audit import green_seconds

HERE = Path(__file__).resolve().parent
TARGETS = {
    'SC105_N_SC1002_to_S_SC1005': (105, 4),
    'SC105_E_SC1_to_S_SC1005': (105, 6),
    'SC105_W_SC1003_to_S_SC1005': (105, 2),
    'SC1005_N_SC105_to_E_SC107': (1005, 7),
    'SC1005_N_SC105_to_W_SC1004': None,
}


def main():
    assert not (HERE / 'service_review.json').exists()
    cfg, _, _ = pickle.loads(audit.blob(audit.A / 'transfer331/build3300_v2/initial.pickle'))
    source = Path(audit.read(audit.A / 'transfer331/build3300_v2/summary.json')['source'])
    response = audit.read(audit.OUT / 'recorded.response.json.gz')
    resources = {(x['resource'], x['start_sec'], x['kind']): x for x in response['resource_allocations']}
    stem = source.name.removeprefix('decisions_')
    paths = {sc: source.parent / 'vissim_eval' / f'{stem}_{sc}_001.ldp' for sc in (105, 1005)}
    ldp = read_ldp_frames(paths, {105: list(range(1,9)), 1005: list(range(1,9))}, 3300, 3750)
    assert len(ldp['frames']) == 451
    audit.PINS.update({p: v['sha256'] for p, v in ldp['pins'].items()})
    rows = []
    for start in (3300, 3450, 3600):
        control = audit.read(source / f'action_{start:06}.json')
        for movement, head in TARGETS.items():
            rate = cfg.network.movement_capacity_by_movement_veh_h[movement]
            total, ticks = Counter(), []
            for t in range(start, start+150, 10):
                stock = resources[movement, t, 'urban_movement_stock']
                request = resources[movement, t, 'urban_movement_intended_limit']
                q, wanted, accepted = stock['available_veh'], request['available_veh'], request['accepted_total_veh']
                green = 10. if head is None else green_seconds(control, cfg.network, movement, t)
                cap = rate * green / 3600
                assert -1e-8 <= accepted <= wanted+1e-8 and wanted <= min(q, cap)+1e-7, (movement, t, q, wanted, cap)
                rec = dict(sec=t, ready=q, green_sec=green, cap=cap, accepted=accepted,
                           ready_stock_shortfall=max(0.,cap-q), other_request_loss=min(q,cap)-wanted,
                           receiving_loss=wanted-accepted)
                ticks.append(rec)
                for k in ('green_sec','cap','accepted','ready_stock_shortfall','other_request_loss','receiving_loss'):
                    total[k] += rec[k]
            assert abs(total['cap']-sum(total[k] for k in ('accepted','ready_stock_shortfall','other_request_loss','receiving_loss'))) < 1e-7
            native_green = None if head is None else sum(ldp['frames'][t][f'{head[0]}:{head[1]}']=='GREEN' for t in range(start,start+150))
            rows.append(dict(start_sec=start, movement=movement, rate_veh_h=rate, native_green_sec=native_green,
                             **dict(total), ticks=ticks))
    result = dict(status='complete_saved_trace_service_decomposition', rows=rows, source_pins=audit.PINS,
                  limitations=['Shared-lane native counts do not identify individual turns.',
                               'Ready-stock shortfall is arithmetic within the retained model, not proof of native demand shortage.',
                               'LDP is native1s signal state; this is not a full-run actuator audit.',
                               'No fitted coefficients, rollout, AD, optimizer, native, or FZP read.'])
    (HERE / 'service_review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    for r in rows:
        print({k: round(v,3) if isinstance(v,float) else v for k,v in r.items() if k!='ticks'})


if __name__ == '__main__':
    main()
