"""SC101 readiness/service/timing audit of completed forecasts and native logs.

No forecasts, fitted coefficients, FZP reads, or running-source changes.
"""
from collections import Counter, defaultdict
from pathlib import Path
import gzip
import hashlib
import importlib.util
import json
import math
import pickle
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
A, H, ROOT = HERE.parent, HERE.parent.parent, HERE.parents[4]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import signal_actuation_contract as signals
from diagnostics.validate_native_signal_record import read_ldp_frames

spec = importlib.util.spec_from_file_location('heads299', H/'sc12_source/audit.py')
head = importlib.util.module_from_spec(spec)
spec.loader.exec_module(head)
head.LINKS = {'SC101_S': 1220011503, 'SC1_S': 1220006903}
M = 'SC101_S_SC1_to_N_SC2005'
SRC = 'movement:'+M
PINS = {}


def pin(path):
    path = Path(path)
    data = path.read_bytes()
    PINS[str(path.resolve())] = hashlib.sha256(data).hexdigest()
    return data


def read(path):
    return json.loads(pin(path))


def tup(value):
    return tuple(tup(x) for x in value) if isinstance(value, list) else value


def green_seconds(control, net, start, dt):
    c = net.signal_actuation_contract
    node = c['nodes']['SC101']
    values = tuple(control['green_times']['SC101_'+p] for p in signals.PHASES)
    windows = signals._phase_windows(tup(node['_segments']), tup(node['_order']), values,
        c['amber']+c['all_red'], signals._native_payload(node), c['amber'])
    assert node['native_clock_basis']['kind'] == 'serial'
    lo, hi = windows['p1']
    return dt*signals._finite_fraction(node['native_clock_basis']['cycle_sec'],
        control['offsets']['SC101'], lo, hi, dt, start, start+dt)


def main():
    assert not (HERE/'assessment.json').exists(), 'Preserve completed diagnostic'
    assert signals._finite_fraction(150., 0., 0., 50., 10., 0., 10.) == 1.
    prior = read(A/'combined298/completion.json')
    assert prior['status'] == 'complete_combined_diagnostic_not_adopted'
    for path, digest in prior['source_pins'].items():
        assert hashlib.sha256(pin(path)).hexdigest() == digest, path
    for rel in ('sc101_recombined/README.md', 'service_ceiling/README.md'):
        pin(H/rel)
    for rel in ('diag_c3/C3_DIAGNOSIS.md', 'diag_c3_r2/U7.md'):
        pin(H.parent/'upstream_worklog/02_urban_b2'/rel)
    cfg, state, _ = pickle.loads(pin(A/'citysplit287/forecast2400/initial.pickle'))
    net = cfg.network
    rate = net.movement_capacity_by_movement_veh_h[M]
    tree = ET.fromstring(pin(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'))
    positions = {int(x.get('lane').split()[1]): float(x.get('pos'))
        for x in tree.findall('./signalHeads/signalHead') if x.get('lane').split()[0]=='1220011503'}
    roots = dict(hold=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold'),
        city=Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected'))
    native, model = {}, {}
    initial_native = None
    for arm, root in roots.items():
        label = 'hold' if arm=='hold' else 'selected'
        stem = f'sdmpc31_g_2400_{label}_s29'
        folder = root/f'decisions_{stem}'
        raw = read(folder/'state_002400.json')['vehicle_records']
        assert raw['complete']
        if initial_native is None:
            initial_native = raw['records']
        else:
            assert initial_native == raw['records']
        initial_ids = {v['veh_no']: v for v in initial_native}
        terminal = {v['veh_no']: v for v in initial_native if v['link_no']==1220011503
            and v['lane_no'] in (1,2,3) and v['position_m']<=positions[v['lane_no']]}
        ldp = read_ldp_frames({101: root/'vissim_eval'/f'{stem}_101_001.ldp'}, {101:list(range(1,9))}, 2400,2850)
        for p, details in ldp['pins'].items():
            PINS[p] = details['sha256']
        frames = ldp['frames']
        assert len(frames)==451
        blocks, events_all, source_history = [], [], defaultdict(list)
        for end in (2250,2400,2550,2700,2850):
            counts, events = head.heads_and_entries(folder,end)
            for lane, veh, sec in events['SC1_S']:
                if lane in (2,3,4):
                    source_history[veh].append(sec)
            if end<=2400:
                continue
            rows = [dict(lane=l,veh=v,sec=t) for l,v,t in events['SC101_S'] if l in (1,2,3)]
            count = sum(x['crossings'] for x in counts['SC101_S']['rows'] if x['lane'] in (1,2,3))
            assert count==len(rows), 'SC101 missing timestamp: use bounds before a timing claim'
            events_all.extend(rows)
            travel = [v['sec']-max(t for t in source_history[v['veh']] if t<v['sec']) for v in rows
                if any(t<v['sec'] for t in source_history[v['veh']])]
            green = [t for t in range(end-150,end) if frames[t]['101:8']=='GREEN']
            blocks.append(dict(start_sec=end-150,count=count,green_sec=len(green),
                head_time_cost=-sum((2850-v['sec'])/3600 for v in rows),
                initial_terminal_crossings=sum(v['veh'] in terminal for v in rows),
                initial_anywhere_crossings=sum(v['veh'] in initial_ids for v in rows),
                initial_origin_counts=dict(Counter(str(initial_ids[v['veh']]['link_no']) if v['veh'] in initial_ids
                    else 'after_initial' for v in rows)),
                source_SC1_S_observed_lower_bound=sum(x['crossings'] for x in counts['SC1_S']['rows'] if x['lane'] in (2,3,4)),
                known_source_to_head_travel_sec=sorted(travel),
                native_first30_head=sum(v['sec']<end-120 for v in rows)))
        native[arm] = dict(blocks=blocks,events=events_all,
            initial_terminal=dict(count=len(terminal),stopped=sum(v['stopped'] for v in terminal.values()),
                lanes=dict(Counter(v['lane_no'] for v in terminal.values()))))

        r = json.loads(gzip.decompress(pin(A/'combined298/forecast2400'/f'{arm}.response.json.gz')))
        resources = {(x['start_sec'],x['kind']):x for x in r['resource_allocations'] if x['resource']==M}
        blocks = []
        for block_index, start in enumerate((2400,2550,2700)):
            cp = (H/'selection2400_discrete/hold' if arm=='hold' else A/'citysplit287/forecast2400/city_only')/f'action_{start:06}.json'
            control = read(cp)
            metrics = dict(service_opportunity=0.,not_ready_opportunity=0.,other_request_loss=0.,
                receiving_loss=0.,accepted=0.,green_sec=0.,head_time_cost=0.)
            ticks = []
            for t in range(start,start+150,10):
                green = green_seconds(control,net,t,10)
                s, q = resources[t,'urban_movement_stock'], resources[t,'urban_movement_intended_limit']
                ready, wanted, accepted = s['available_veh'], q['available_veh'], q['accepted_total_veh']
                cap = rate*green/3600.
                assert -1e-8<=accepted<=wanted+1e-8 and wanted<=min(ready,cap)+1e-7, (arm,t,ready,cap,wanted)
                metrics['service_opportunity']+=cap
                metrics['not_ready_opportunity']+=max(0.,cap-ready)
                metrics['other_request_loss']+=min(ready,cap)-wanted
                metrics['receiving_loss']+=wanted-accepted
                metrics['accepted']+=accepted
                metrics['green_sec']+=green
                metrics['head_time_cost']-=accepted*(2850-t)/3600.
                inflow=sum(v['vehicles'] for v in r['transfers'] if v['start_sec']==t and v['target']==SRC and v['source']!=SRC)
                ticks.append(dict(sec=t,green_sec=green,ready=ready,service_budget=cap,wanted=wanted,
                    accepted=accepted,arrived_to_movement=inflow,native_head_count=sum(t<=v['sec']<t+10 for v in events_all),
                    native_green_sec=sum(frames[s]['101:8']=='GREEN' for s in range(t,t+10))))
            assert abs(metrics['service_opportunity']-metrics['not_ready_opportunity']-metrics['other_request_loss']-
                metrics['receiving_loss']-metrics['accepted'])<1e-7
            actual_transfer=sum(v['vehicles'] for v in r['transfers'] if start<=v['start_sec']<start+150 and v['source']==SRC and v['target']!=SRC)
            assert abs(actual_transfer-metrics['accepted'])<1e-7
            incoming=Counter()
            for v in r['transfers']:
                if start<=v['start_sec']<start+150 and v['target']=='storage:SC1_to_SC101' and v['source']!=v['target']:
                    incoming[v['source'] or v['route_key']]+=v['vehicles']
            blocks.append(dict(start_sec=start,metrics=metrics,ticks=ticks,source_to_corridor=dict(incoming)))
        model[arm] = dict(rate_veh_h=rate,initial_ready=state.urban_movement_queue[M],blocks=blocks)
    PINS.update(head.PINS)
    pin(Path(__file__))
    report=dict(status='complete_cached_SC101_readiness_clock_audit',model=model,native=native,source_pins=PINS,
        previous_goal_turn='no_progress: the user-facing FW5 reply restated already verified settings; this turn audits fresh residual evidence',
        budget=dict(forecasts=0,ad=0,optimizer=0,native=0,fzp=0,new_fits=0,production_changes=0),goal_complete=False,
        limitations=['Opportunity decomposition uses recorded operands, not a counterfactual forecast.',
            'SC101 head-time cost is a timing diagnostic, not its total causal Omega contribution.',
            'SC1 lanes2..4 provide a source-flow lower bound; lane5 turns and other incoming legs are not included.',
            'Actual native1s green and model10s accounting are distinguished; event timestamps retain0.1s precision.',
            'Initial physical terminal inventory is not automatically ready at the stopline.',
            'No future observation was supplied to a plant forecast.'])
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for arm in roots:
        print(arm,'NATIVE', [{k:v for k,v in b.items() if k not in ('known_source_to_head_travel_sec','initial_origin_counts')} for b in native[arm]['blocks']])
        print(arm,'MODEL',[b['metrics'] for b in model[arm]['blocks']])
    print('AUDIT_DONE',HERE/'assessment.json')


if __name__=='__main__':
    main()
