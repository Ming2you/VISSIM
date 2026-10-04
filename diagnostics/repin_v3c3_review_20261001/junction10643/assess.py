"""Assess the one junction-aligned candidate against completed common-state runs."""
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}


def read(path):
    data=path.read_bytes();PINS[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(gzip.decompress(data) if path.suffix=='.gz' else data)


def labels(snapshot):
    counts=Counter()
    for cell in snapshot['cells']:
        for packet in cell['packets']:
            counts[tuple(packet['label'])]+=packet['vehicles']
    return counts


def local_totals(snapshot):
    n=Counter()
    for c in snapshot['cells']:
        road,lane,cell=c['cell'];key=('126+10641' if road in (126,10641) else str(road))+':'+str(lane)
        n[key]+=c['stock']
    return dict(n)


def head_flows(trace):
    out=Counter()
    for r in trace['local_receiver_diagnostics']['resources']:
        if r['kind']!='lane_urban_sending':continue
        key=ast.literal_eval(r['resource'])
        if key[0]=='external':continue
        road,lane,cell=key
        if road==71 and cell==3:
            connector=10634 if lane<=3 else 10635
            out[str(lane)]+=r['accepted_by_source_veh'].get(str(('exit',connector)),0.)
    return dict(out)


def main():
    assert not (HERE/'assessment.json').exists()
    protocol=read(HERE/'protocol.json')
    executed=read(HERE/'executed_sources.json')
    for p,h in executed.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    cfg=read(HERE/'candidate_config.json');base_cfg=read(HERE.parent/'retained10638/candidate_config.json')
    manifest=read(ROOT/cfg['freeway']['lane_plant']);base_manifest=read(ROOT/base_cfg['freeway']['lane_plant'])
    candidate_protocol=read(ROOT/manifest['sources']['reference_protocol']['path'])
    base_protocol=read(ROOT/base_manifest['sources']['reference_protocol']['path'])
    assert candidate_protocol.pop('junction_aligned_10643') is True
    assert candidate_protocol==base_protocol
    manifest['qualification']=base_manifest['qualification']
    manifest['sources']['reference_protocol']=base_manifest['sources']['reference_protocol']
    assert manifest==base_manifest
    cfg['freeway']['lane_plant']=base_cfg['freeway']['lane_plant'];assert cfg==base_cfg
    native=read(HERE.parent/'retained10638/assessment.json')
    cases={};mass=route=resource=0.;wall=0.;n=0
    for seed,old in [('47','entry10643'),('43','retained43')]:
        prefix='closedloop_recorded2700_select_check_trace10681_' if seed=='47' else 'closedloop_recorded2250_lever450_trace10681_'
        folder=I/(prefix+'junction10643_'+seed);old_folder=I/(prefix+old)
        summary=read(folder/'summary.json');base=read(old_folder/'summary.json')
        assert not summary['future_observation_inputs'] and not summary['native_started']
        assert set(summary['results'])==set(base['results'])
        cases[seed]={}
        for key,r in summary['results'].items():
            arm=('hold' if seed=='47' else 'nc') if key=='held_actual' else key
            before=base['results'][key];assert r['commands']==before['commands']
            tr=read(folder/(key+'_RM_C10681_trace.json.gz'));old_tr=read(old_folder/(key+'_RM_C10681_trace.json.gz'))
            assert tr['offramp_network_diagnostics']['states'][0]==old_tr['offramp_network_diagnostics']['states'][0]
            assert tr['mainline_diagnostics']['initial_and_block_states'][0]==old_tr['mainline_diagnostics']['initial_and_block_states'][0]
            a=tr['local_receiver_diagnostics']['states'][0];b=old_tr['local_receiver_diagnostics']['states'][0]
            for field in ('pending','unrouted_pending','off_lanes','arrival_tags','entry_paths','future_shares'):
                assert a[field]==b[field],field
            la,lb=labels(a),labels(b)
            assert set(la)==set(lb) and max(abs(la[k]-lb[k]) for k in la)<1e-7
            assert abs(sum(c['capacity'] for c in a['cells'])-sum(c['capacity'] for c in b['cells']))<1e-7
            route=max(route,max(c['max_cell_residual'] for c in r['offramp_route_inventory_checks']))
            resource=max(resource,max(c['exceedance_veh'] for c in tr['local_receiver_diagnostics']['resources']))
            ports={}
            for off,p in tr['offramp_network_diagnostics']['states'][-1]['ports'].items():
                ref=native['cases'][seed][arm]['ports'][off]
                ports[off]=dict(native=ref['native'],before=ref['after'],after=dict(entry=p['admitted'],drain=p['departed'],final_stock=p['stock']))
                mass=max(mass,abs(p['stock']-p['initial']-p['admitted']+p['departed']))
            cases[seed][arm]=dict(ports=ports,heads_before=head_flows(old_tr),heads_after=head_flows(tr),
                local_final_before=local_totals(old_tr['local_receiver_diagnostics']['states'][-1]),
                local_final_after=local_totals(tr['local_receiver_diagnostics']['states'][-1]),
                costs=dict(native_delta=native['cases'][seed][arm]['costs']['native_delta'],
                    before_delta=before['ttt_omega_veh_h']-base['results']['held_actual']['ttt_omega_veh_h'],
                    after_delta=r['ttt_omega_veh_h']-summary['results']['held_actual']['ttt_omega_veh_h'],
                    before_omega=before['ttt_omega_veh_h'],after_omega=r['ttt_omega_veh_h'],
                    before_outside=before['tracked_outside_residence_veh_h'],after_outside=r['tracked_outside_residence_veh_h']),
                ramps_before=before['ramps'],ramps_after=r['ramps'])
            n+=1;wall+=r['wall_sec']
            print(seed,arm,'PORT10643',ports['10643'],'COSTS',cases[seed][arm]['costs'])
            print('HEAD',cases[seed][arm]['heads_after'],'LOCAL',cases[seed][arm]['local_final_after'])
    assert n==6 and max(mass,route,resource)<1e-7
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert hashlib.sha256(stop.read_bytes()).hexdigest()==protocol['stop_sha256']
    out=dict(status='completed_geometry_candidate_pending_adoption',cases=cases,forecasts=n,
        compute_sec=wall,off_mass_residual=mass,route_residual=route,resource_exceedance=resource,
        source_pins=PINS,stop_sha256=protocol['stop_sha256'],new_native=0,new_fzp_scans=0,new_fits=0,
        limitations=['126 tail is computationally owned by10641; combine126+10641 when comparing physical stock.',
        'Initial labels and total storage are conserved, but finite-volume projection changes positions inside cells.',
        '47 pair changes city signals, not RM/VSL.43 was previously examined; neither is a new blind holdout.',
        'Compiled/AD rejected for this candidate; scalar physical validation alone cannot qualify controller9000.'])
    (HERE/'assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('COMPLETED_SIX',wall,mass,route,resource)


if __name__=='__main__':main()
