"""Reaggregate the verified native pairs to Omega701 and assess saved forecasts."""
import argparse,csv,gzip,hashlib,json,math
from collections import defaultdict
from pathlib import Path
from assess import targets,digest,ROOT,HERE
read=lambda p:json.loads(Path(p).read_bytes())

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    assert not (a.out/'matched_assessment.json').exists()
    summary=read(a.out/'summary.json');assert summary['status']=='complete_conditional_pair'
    seed,start=summary['seed'],summary['start'];arms=list(summary['results'])
    native_receipt=read(a.out/'fixed_replay_receipt.json')
    native_path=Path(native_receipt['native_summary']);proof=read(native_path)
    assert proof['paired_prefix_exact'] and proof['common_start_vehicle_records_exact']
    assert proof['counterfactual_valid'] or native_receipt['comparison_scope']['paired_native_effect_valid']
    for arm in arms:assert proof['arms'][arm]['native_execution_passed']
    config=HERE/'legacy_urban_diagnostic_config.json';membership=ROOT/read(config)['control_area_objective']['membership_path']
    inside=set(map(str,read(membership)['inside_links']));assert len(inside)==701
    g=read(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json')
    chain={str(v['link']):road for road,values in g['chains'].items() for v in values}
    ramps={str(v['connector']) for v in g['boundaries'] if v['kind']=='ramp'}
    pins={str(membership):digest(membership),str(native_path):digest(native_path),str(Path(__file__)):digest(__file__)}
    native_cost={};model_cost={};evidence={};snapshots={}
    for arm in arms:
        metric_path=native_path.parent/arm/'area_metrics.json';metric=read(metric_path);pins[str(metric_path)]=digest(metric_path)
        cost=dict(omega=0.,east=0.,west=0.,ramps=0.,other=0.,outside=0.)
        for link,row in metric['physical_link_residence'].items():
            n=row['ttt_veh_h']
            if link not in inside:cost['outside']+=n;continue
            cost['omega']+=n;key={'FW_E':'east','FW_W':'west'}.get(chain.get(link),'ramps' if link in ramps else 'other');cost[key]+=n
        assert abs(cost['omega']-sum(cost[k] for k in ('east','west','ramps','other')))<1e-7
        native_cost[arm]=cost
        result=summary['results'][arm];m=result['costs_by_stock'];mc=dict(omega=result['ttt'],east=m['freeway:FW_E'],west=m['freeway:FW_W'],
            ramps=sum(v for k,v in m.items() if k.startswith('ramp:')),outside=sum(result['outside_costs_by_stock'].values()))
        mc['other']=mc['omega']-mc['east']-mc['west']-mc['ramps'];model_cost[arm]=mc
        folder=Path(native_receipt['candidate_actions'][arm][0]).parent
        obs,more=targets(folder,start,config);pins.update(more)
        predicted=read(a.out/(arm+'_snapshots.json'));snapshots[arm]=[]
        initial=max(abs(x-y) for fw in obs[0]['n'] for x,y in zip(obs[0]['n'][fw],predicted[0]['n'][fw]));assert initial<1e-7
        for native,pred in zip(obs,predicted):
            assert native['time_sec']==pred['time_sec']
            snapshots[arm].append(dict(time_sec=native['time_sec'],actual=native,predicted=pred))
        raw=read(folder/f'state_{start:06}.json');dc=raw['obs150']['detector_config'];blob=Path(dc['path']).read_bytes()
        assert hashlib.sha256(blob).hexdigest()==dc['sha256']
        detectors=list(csv.DictReader(blob.decode('utf-8-sig').splitlines()));refs=defaultdict(list)
        for row in detectors:
            if row['role'] in ('off_entry','chain_end','source'):refs[row['boundary_ref']].append(row['dcm_no'])
        flow={ref:dict(actual=[sum(v['obs150_detectors'][key] for key in keys) for v in obs[1:]],predicted=[0.,0.,0.]) for ref,keys in refs.items()}
        response=json.loads(gzip.decompress((a.out/(arm+'_response.json.gz')).read_bytes()))
        for tr in response['transfers']:
            source,target=tr['source'],tr['target'];ref=None
            if source in ('freeway:FW_E','freeway:FW_W'):
                if target.startswith('transit:exchange:off:'):ref='off_entry:'+target.split(':')[-1]
                elif target.startswith('external:terminal:'):ref='chain_end:'+target.split(':')[-1]
            elif source in ('origin:FW_E','origin:FW_W') and target=='freeway:'+source.split(':')[-1]:ref='source:'+source.split(':')[-1]
            if ref is None:continue
            block=int((tr['end_sec']-start-1e-7)//150);assert 0<=block<3 and tr['start_sec']>=start+150*block-1e-7
            flow[ref]['predicted'][block]+=tr['vehicles']
        evidence[arm]=flow
    left,right=arms
    nd={k:native_cost[right][k]-native_cost[left][k] for k in native_cost[left]}
    md={k:model_cost[right][k]-model_cost[left][k] for k in model_cost[left]}
    report=dict(status='complete_descriptive_pair_assessment_not_full348_validation',seed=seed,start=start,end=start+450,arms=arms,
        native_delta=nd,model_delta=md,flows=evidence,physical31_snapshots=snapshots,
        whole_omega_links=701,native_reaggregation='Cached full physical-link residence difference; exact common prefix cancels. Not absolute450s native costs.',
        nominal110_vs90_only=True,source_pins=pins,forecasts_added=0,fits=0,new_native=0,
        caveats=['Current freeway5/urban10 model with the native348 urban recipe explicitly excluded.',
            'Native5s sampling plus final4.9s tail hold differs from10s model quadrature.',
            'Known seeds used previously; not blind validation. Future observation is assessment only.',
            'Native outside residence covers all observed outside links; model outside costs cover model stocks only.',
            'Actual future source insertion differences are not injected as forecast demand.',
            'Native detector at1m and model port can differ spatially. No NP/NUF selection claim.'])
    (a.out/'matched_assessment.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(seed=seed,native_delta=nd,model_delta=md,flows={arm:{k:v for k,v in e.items() if k in ('off_entry:10483','chain_end:FW_E','source:FW_E')} for arm,e in evidence.items()}),indent=2))

if __name__=='__main__':main()
