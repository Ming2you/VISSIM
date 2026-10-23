"""Attribute the completed three forecasts' approach-speed terms; no rollout."""
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import copy
import gzip
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent
HERE = OUT.parent
ROOT = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
CACHE = HERE/'matched_off2250_v3'
PINS = {}


def read(path):
    path = Path(path)
    blob = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(blob).hexdigest()
    return json.loads(gzip.decompress(blob) if path.suffix == '.gz' else blob)


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def main():
    assert not (OUT/'approach_terms_summary.json').exists(), 'Reuse completed evidence'
    sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
    from evaluation.controllers import lane_plant_runtime as lpr, freeway_fd as fd
    from evaluation.controllers import area_freeway_accounting as accounting
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from src.models.state import ControlAction
    tuning = read(ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json')
    context = lpr.load_sources(tuning['freeway']['lane_plant'])
    component = context['component']
    cfg = component._config('FW_E', context['parameters']['by_direction']['FW_E'])
    net, mn = cfg.network, accounting._mn
    assert not component.lane_groups_enabled
    assert float(getattr(net, 'capacity_drop_discharge_phi', 1) or 1) == 1
    assert not (getattr(net, 'freeway_hadiuzzaman', {}) or {}).get('FW_E')
    active = read(HERE/'cached_vsl_exposure_audit_v2/active_component_config.json')
    params = net.freeway_segment_params['FW_E']
    assert params == active['parameters']
    parent = read(CACHE/'network.json')
    heads = parent['freeway_vsl_zone_heads']['FW_E']
    net.freeway_vsl_zone_heads['FW_E'] = heads
    net.freeway_vsl_zone_head_of_cell['FW_E'] = active['head_of_physical_cell']
    net.freeway_vsl_zone_of_cell['FW_E'] = [heads.index(h) for h in active['head_of_physical_cell']]
    net.freeway_vsl_zone_free = tuning['freeway']['vsl_zone_free']
    branches = {str(b['connector']): b['from_cell'] for b in context['geometry']['boundaries'] if b['road']=='FW_E' and b['kind']=='offramp'}
    merges = {'RM_C'+str(b['connector']): b['to_cell'] for b in context['geometry']['boundaries'] if b['road']=='FW_E' and b['kind']=='ramp'}
    selected = tuple(range(14,19))
    assert not set(selected).intersection(merges.values())
    lengths = [p['segment_length_km'] for p in params]
    cached = read(CACHE/'summary.json')
    report = dict(status='in_progress', new_native=0, new_forecasts=0, new_fzp_scans=0,
                  production_edits=0, cases={}, source_pins=PINS,
                  max_stock_error=0., max_recorded_speed_error=0., max_formula_error=0.)
    for p in [Path(__file__), Path(accounting.__file__), Path(adapter.__file__), Path(fd.__file__), *context['paths'].values()]:
        PINS[str(p)] = hashlib.sha256(Path(p).read_bytes()).hexdigest()
    for result in cached['results']:
        name = result['name']
        response = read(CACHE/f'{name}_response.json.gz')
        targets = read(HERE/'cached_vsl_exposure_audit_v2'/f'{name}_rows.json.gz')
        target = {(r['start_sec'],r['end_sec'],r['cell']): r for r in targets}
        steps = defaultdict(dict)
        for x in response['resource_allocations']:
            kind, res = x['kind'], x['resource']
            field, index = None, None
            if kind=='freeway_mainline_sending' and res.startswith('FW_E:cell:'): field,index='sending',int(res.split(':')[-1])
            elif kind=='freeway_mainline_receiving_after_ramps' and res.startswith('FW_E:cell:'): field,index='receiving',int(res.split(':')[-1])
            elif kind=='freeway_terminal_sending' and res=='FW_E': field,index='sending',30
            elif kind=='freeway_entry_request' and res=='FW_E': field,index='entry',0
            elif kind=='freeway_entry_receiving_after_ramps' and res=='FW_E': field,index='receiving',0
            elif kind=='freeway_offramp_sending' and res in branches: field,index='off',res
            if field:
                row=steps[(x['start_sec'],x['end_sec'])].setdefault(field,{})
                assert index not in row
                row[index]=x
        for x in response['transfers']:
            if x['source'] in {'merge_pending:'+r for r in merges} and x['target']=='freeway:FW_E':
                steps[(x['start_sec'],x['end_sec'])].setdefault('merge',defaultdict(float))[x['source'].split(':',1)[1]] += x['vehicles']
        frames={f['end_sec']:f for f in response['freeway_frames']}
        n=list(result['snapshots'][0]['n']['FW_E'])
        source=[]
        for (start,end),s in sorted(steps.items()):
            dt=end-start
            assert set(s['sending']) == set(s['receiving']) == set(range(31))
            q=[s['sending'][i]['accepted_total_veh'] for i in range(31)]
            requested=[s['sending'][i]['available_veh'] for i in range(31)]
            off,rv=[0.]*31,[0.]*31
            for o,x in s['off'].items():
                off[branches[o]]+=x['accepted_total_veh']; requested[branches[o]]+=x['available_veh']
            for r,amount in s.get('merge',{}).items(): rv[merges[r]]+=amount
            lanes=[(s['receiving'][i]['available_veh']+rv[i]+n[i])/(net.rho_max*lengths[i]) for i in range(31)]
            rho=[n[i]/(lengths[i]*lanes[i]) for i in range(31)]
            speeds=[requested[i]*3600/dt*lengths[i]/n[i] if n[i]>1e-8 else None for i in range(31)]
            clipped=[abs(requested[i]-n[i])<1e-7 for i in range(31)]
            entry=s['entry'][0]['accepted_total_veh']
            nextn=[n[i]+(entry if i==0 else q[i-1])+rv[i]-q[i]-off[i] for i in range(31)]
            if end in frames:
                expected=[sum(row.values()) for row in frames[end]['offramp_route_inventory_state']['cells']['FW_E']]
                error=max(abs(a-b) for a,b in zip(nextn,expected))
                report['max_stock_error']=max(report['max_stock_error'],error)
                assert error<1e-7
            source.append(dict(start=start,end=end,n=n,rho=rho,speed=speeds,lanes=lanes,clipped=clipped,
                               off_cap={branches[o]:x['accepted_total_veh']<x['available_veh']-1e-9 for o,x in s['off'].items()}))
            n=nextn
        rows=[]
        for j,r in enumerate(source):
            dt=r['end']-r['start']
            frame=next(f for f in response['freeway_frames'] if f['start_sec']<=r['start']+1e-8 and r['end']<=f['end_sec']+1e-8)
            action=ControlAction(**frame['applied_control'])
            adapter._FW_SEG_CTX_STATE['profile']={'FW_E':r['lanes']}
            for i in selected:
                assert not r['clipped'][i] and not r['clipped'][i-1] and not r['off_cap'].get(i,False)
                p=params[i];v=r['speed'][i];up=r['speed'][i-1];rho=r['rho'][i];down=r['rho'][i+1]
                stored=target[(r['start'],r['end'],i)]
                assert abs(stored['rho']-rho)<1e-7
                desired=stored['mixed_target']
                shown=mn.segment_vsl(action,'FW_E',i,cfg)
                assert float(shown)==stored['displayed']
                nu0=mn.select_anticipation_nu(rho,net,shown)
                ctx=copy.deepcopy(adapter._FW_SEG_CTX);assert ctx['armed']
                tau,nu=fd.state_response_coefficients(fd.cell_state_response(net,'FW_E',i),v,desired,rho,down,ctx['response_rho_crit'],p['metanet_tau_h'],nu0)
                relax=(desired-v)/(tau*3600)
                conv=v*(up-v)/(lengths[i]*3600)
                anti=-nu*(down-rho)/(tau*lengths[i]*3600*(rho+p['metanet_kappa_veh_km_lane']))
                loss=ctx['phi']*ctx['dlam']*rho*v*v/(3600*lengths[i]*max(ctx['lanes'],1e-9)*p['rho_crit']) if ctx['phi']>0 and ctx['dlam']>0 else 0.
                actual=mn.metanet_speed_update_kmh(v,up,rho,down,desired,dt/3600,lengths[i],net.metanet_tau_h,nu0,net.metanet_kappa_veh_km_lane,net.v_min)
                direct=max(net.v_min,max(net.v_min,v+dt*(relax+conv+anti))-dt*loss)
                report['max_formula_error']=max(report['max_formula_error'],abs(actual-direct))
                expected=source[j+1]['speed'][i] if j+1<len(source) else result['snapshots'][-1]['speed']['FW_E'][i]
                report['max_recorded_speed_error']=max(report['max_recorded_speed_error'],abs(actual-expected))
                assert abs(actual-direct)<1e-7 and abs(actual-expected)<2e-5,(name,j,i,actual,expected)
                rows.append(dict(start_sec=r['start'],end_sec=r['end'],cell=i,n=r['n'][i],rho=rho,v=v,upstream_v=up,downstream_rho=down,
                                 desired=desired,relaxation=relax,convection=conv,anticipation=anti,lane_drop=-loss,
                                 direct_vsl_relaxation=stored['direct_target_delta']/(tau*3600),fraction90=stored['fraction90']))
        summary=[]
        for block in range(3):
            for i in selected:
                part=[r for r in rows if r['cell']==i and 2250+150*block<=r['start_sec']<2400+150*block]
                assert abs(sum(r['end_sec']-r['start_sec'] for r in part)-150)<1e-7
                mean={k:sum(r[k]*(r['end_sec']-r['start_sec']) for r in part)/150 for k in rows[0] if k not in ('start_sec','end_sec','cell')}
                summary.append(dict(block=block,cell=i,**mean))
        report['cases'][name]=dict(event_steps=len(source),terms=len(rows),summary=summary)
        (OUT/f'{name}_approach_terms.json.gz').write_bytes(gzip.compress(json.dumps(rows,allow_nan=False).encode()))
        print(name,'verified local terms',len(rows),flush=True)
    for path,h in PINS.items(): assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,path
    report['status']='verified_approach14_18_cached_terms'
    report['limitations']=['Instantaneous model equation terms are not observed vehicle accelerations or independent causal effects.',
                          'No fitted coefficients, corrected forecast, or adopted production change.']
    save(OUT/'approach_terms_summary.json',report)
    print(json.dumps({k:v for k,v in report.items() if k.startswith('max_')}),flush=True)


if __name__=='__main__': main()
