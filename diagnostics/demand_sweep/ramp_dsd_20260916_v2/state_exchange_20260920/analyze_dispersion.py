"""Post-run exact initial replay, local conservation and distribution contrasts."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from evaluation.controllers.desired_speed_transport import SpeedDistribution
from collections import defaultdict,Counter
import math
import re
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent;H=HERE.parent
BOUNDS=[(400.,1305.3887036831929),(1305.3887036831929,1651.8060404357457),
        (1651.8060404357457,1964.2176840051573),(1964.2176840051573,2307.3794608258345),
        (2307.3794608258345,2652.027349)]


def records(path):
    with path.open('rb') as stream:
        for line in stream:
            if line[:1].isdigit():yield line.rstrip(b'\r\n;').split(b';')


def analyze(run,geometry,distribution=None,reference=None):
    path=run/'vissim_eval/baseline_001.fzp';observer=Observer(geometry)
    main={int(k) for k,v in geometry['addresses'].items() if v[0]=='FW_E'}
    ports={b['connector']:('on' if b['kind']=='ramp' else 'off') for b in geometry['boundaries']
           if b['road']=='FW_E' and b['kind'] in ['ramp','offramp']}
    source_links={int(k) for k in geometry['sources']}
    parts=Counter();previous={};local=[Counter() for _ in BOUNDS];gates=Counter();births=Counter();seen=set()
    errors=[];pending={};sample_examples=[];before_count=0
    ref=iter(records(reference)) if reference else None
    root=ET.parse(H/'dsd_response_20260920/native_v2/prepared/network/baseline.inpx').getroot()
    node=next(x for x in root.findall('./desSpeedDistributions/desSpeedDistribution') if x.get('no')=='120')
    before_cdf=SpeedDistribution(tuple((float(x.get('fx')),float(x.get('x'))) for x in node.findall('./speedDistrDatPts/speedDistributionDataPoint')))
    for p in records(path):
        sec=int(float(p[0]))
        if sec>3000:break
        if ref is not None and sec<=2400:
            before=next(ref)
            if p[:9]!=before[:9]:raise AssertionError(('Pre-control physical divergence',sec,p,before))
            before_count+=1
        vid=int(p[1]);link=int(p[2]);lane=int(p[3]);pos=float(p[4]);v=float(p[6])
        desired=float(p[9]) if len(p)>9 else None
        if (sec,vid) in pending:
            expected=pending.pop((sec,vid));errors.append(desired-expected)
            if len(sample_examples)<5:sample_examples.append({'sec':sec,'vehicle':vid,'expected':expected,'actual':desired})
        old=previous.get(vid)
        if distribution and link==2 and old and old[0]==sec-1 and 2400<sec<=3000:
            old_loc=observer.locate((old[1],old[2],old[3],old[4]));loc=observer.locate((link,lane,pos,v))
            if old_loc and loc and old_loc[0]==loc[0]=='FW_E':
                prior_pos=pos-(loc[2]-old_loc[2])
                if prior_pos<48.185556564965211<=pos:
                    # This is the first controlled DSD. Every upstream mainline
                    # DSD still has distribution120; all four lanes share it.
                    u=before_cdf.fractile(old[5]);pending[sec+1,vid]=distribution.quantile(u)
        if vid not in seen:
            seen.add(vid)
            if 2400<sec<=2850:
                births['all_network']+=1
                if link in source_links:births['source_link_'+str(link)]+=1
        if 2400<sec<=2850:
            if link in main:parts['mainline']+=1
            if link in ports:parts[ports[link]]+=1
            if link==2:
                for i,(a,b) in enumerate(BOUNDS):
                    if a<pos<=b:
                        local[i]['vehicle_seconds']+=1;local[i]['slow30_vehicle_seconds']+=int(v<30)
                        local[i]['lane_changes']+=int(bool(old and old[0]==sec-1 and old[1]==link and old[2]!=lane))
                if old and old[0]==sec-1 and old[1]==link:
                    for gate in [400.,1305.3887036831929]:
                        if old[3]<gate<=pos:gates[str(gate)]+=1
        if link==2 and sec in [2400,2850]:
            for i,(a,b) in enumerate(BOUNDS):
                if a<pos<=b:local[i]['n_'+str(sec)]+=1
        previous[vid]=(sec,link,lane,pos,v,desired)
    balances=local[0]['n_2850']-local[0]['n_2400']-gates[str(400.)]+gates[str(1305.3887036831929)]
    assert balances==0,('Local unexplained disappearance',balances)
    assert not any(abs(x)>.003 for x in errors),('First-DSD desired-speed mismatch',max(map(abs,errors)))
    assert all(t>3000 for t,vid in pending),'Unexplained missing desired-speed readout'
    parts={k:parts[k]/3600 for k in ['mainline','on','off']};parts['total']=sum(parts.values())
    err=(run/'baseline_001.err').read_text(encoding='utf-8',errors='replace')
    removals=[{'time_s':float(t),'vehicle':int(v),'link':int(l)} for t,v,l in re.findall(
        r'Simulation second ([\d.]+):[^\r\n]*?vehicle (\d+)[^\r\n]*?was removed from link (\d+)',err)
        if 2400<float(t)<=2850]
    component_removals=[r for r in removals if r['link'] in main or r['link'] in ports]
    return {'parts':parts,'regions':[{'start_m':a,'end_m':b,**dict(local[i])} for i,(a,b) in enumerate(BOUNDS)],
        'gates':dict(gates),'local_balance_residual':balances,'new_vehicle_counts':dict(births),
        'precontrol_exact_rows':before_count,'first_dsd_verified_crossings':len(errors),
        'first_dsd_max_error_kmh':max(map(abs,errors)) if errors else None,'first_dsd_examples':sample_examples,
        'terminal_censored_desired_records':len(pending),'explicit_component_removals':component_removals,
        'explicit_all_network_removals':len(removals),
        'warnings':'End-of-run remaining input demand includes scheduled future demand after the3000s stop. It is not a measure of failed insertion. First-seen source counts are reported separately.'}


def main():
    out=HERE/'dispersion_analysis_v1';out.mkdir(exist_ok=False)
    base=HERE/'dispersion_native_v1';protocol=e.load(base/'protocol.json')
    geometry=e.ObservationData(H/'controller_response_s23_v1/none').geometry
    ref=H/'dsd_response_20260920/native_v2/run_retry1'
    paths={'none':H/'rules_4500_s23_v1/run_none','actual100':ref,
           **{name:base/name/'run' for name in protocol['cases']}}
    results={}
    for name,run in paths.items():
        dist=None
        if name in protocol['cases']:
            execution=e.load(run/'run.json');validation=e.load(run/'fixed_validation.json')
            assert execution['completed'] and execution['terminal_sec']==3000 and validation['passed']
            dist=SpeedDistribution(tuple((float(p['fx']),float(p['x'])) for p in protocol['cases'][name]['points']))
        result=analyze(run,geometry,dist,ref/'vissim_eval/baseline_001.fzp' if dist else None)
        if dist:assert result['precontrol_exact_rows']>1000000 and result['first_dsd_verified_crossings']>500
        if name in ['none','actual100']:
            arm='none' if name=='none' else 'vsl'
            known=e.load(H/'merge_drain_response_20260919/native_audit_v1/result.json')['23']['arms'][arm]['parts']['FW_E']
            for k,v in known.items():assert abs(result['parts'][k]-v)<1e-8,('Native metric regression',name,k)
        results[name]=result;e.save(out/(name+'.json'),result)
        print('NATIVE',name,result['parts'],flush=True)
    delta={name:{k:r['parts'][k]-results['none']['parts'][k] for k in r['parts']}
           for name,r in results.items() if name!='none'}
    e.save(out/'summary.json',{'results':results,'delta_vs_none_veh_h':delta,
        'mean_spread_interaction_veh_h':delta['affine_both']['total']-delta['mean_only']['total']-delta['spread_only']['total'],
        'reference_shape_difference_veh_h':delta['actual100']['total']-delta['affine_both']['total'],
        'claim_scope':'Single-seed diagnostic, not controller improvement or a population capacity effect',
        'area':'FW_E mainline + four on-ramp and four off-ramp connectors, not Omega'})
    print('DELTAS',delta,flush=True)


def spatial_contrasts():
    """Locate the opposite net effects without fitting any response coefficient."""
    out=HERE/'dispersion_spatial_v2';out.mkdir(exist_ok=False)
    cases={23:{'none':H/'rules_4500_s23_v1/run_none',
               'spread_only':HERE/'dispersion_native_v1/spread_only/run'},
           33:{'none':H/'state_response_20260919/native_s33_v1/run_none',
               'spread_only':HERE/'dispersion_seed33_v1/spread_only/run'}}
    results={}
    for seed,runs in cases.items():
        folder=(H/'controller_response_s23_v1/none' if seed==23 else
                H/'state_response_20260919/native_s33_v1/observations/none')
        geometry=e.ObservationData(folder).geometry;observer=Observer(geometry)
        east={int(k) for k,v in geometry['addresses'].items() if v[0]=='FW_E'}
        ports={b['connector']:b['kind'] for b in geometry['boundaries']
               if b['road']=='FW_E' and b['kind'] in ['ramp','offramp']}
        summaries=e.load(HERE/('dispersion_analysis_v1' if seed==23 else
                              'dispersion_seed33_analysis_v1')/'summary.json')['results']
        arms={}
        for name,run in runs.items():
            counts=defaultdict(Counter);last={};internal34=Counter();cross_group=Counter();unlocated=[]
            for p in records(run/'vissim_eval/baseline_001.fzp'):
                sec=int(float(p[0]))
                if sec<2400:continue
                if sec>2850:break
                link=int(p[2]);lane=int(p[3]);pos=float(p[4]);speed=float(p[6]);vid=int(p[1])
                loc=observer.locate((link,lane,pos,speed))
                key=('cell:'+str(loc[1]) if loc and loc[0]=='FW_E' else
                     'unlocated_mainline:'+str(link) if link in east else
                     'port:'+str(link) if link in ports else None)
                if key is None:continue
                if key.startswith('unlocated_mainline:') and len(unlocated)<10:
                    unlocated.append({'time_s':sec,'vehicle':vid,'link':link,'pos_m':pos})
                old=last.get(vid);last[vid]=(sec,link,lane,key)
                if sec==2400:continue
                row=counts[(key,(sec-2401)//150)]
                row['vehicle_seconds']+=1;row['speed_sum_kmh']+=speed
                row['slow30_vehicle_seconds']+=int(speed<30)
                if old and old[0]==sec-1 and old[1]==link and old[2]!=lane:
                    row['lane_changes']+=1
                    if loc and loc[0]=='FW_E' and 5<=loc[1]<=14 and old[3]==key:
                        if {lane,old[2]}=={3,4}:internal34[key]+=1
                        elif min(lane,3)!=min(old[2],3):cross_group[key]+=1
            rows=[{'address':key,'start_s':2400+150*step,'end_s':2550+150*step,
                   **dict(row),'ttt_veh_h':row['vehicle_seconds']/3600}
                  for (key,step),row in sorted(counts.items())]
            main=sum(r['ttt_veh_h'] for r in rows if not r['address'].startswith('port:'))
            total=sum(r['ttt_veh_h'] for r in rows)
            assert abs(main-summaries[name]['parts']['mainline'])<1e-8,(seed,name,main,summaries[name]['parts'])
            assert abs(total-summaries[name]['parts']['total'])<1e-8,(seed,name,total,summaries[name]['parts'])
            arms[name]={'rows':rows,'within_lanes34_changes':dict(internal34),
                        'between_group_changes':dict(cross_group),'parts':summaries[name]['parts'],
                        'unlocated_mainline_examples':unlocated}
            e.save(out/f's{seed}_{name}.json',arms[name])
            print('SPATIAL',seed,name,round(total,6),flush=True)
        def totals(arm):
            data=defaultdict(float)
            for r in arms[arm]['rows']:data[r['address']]+=r['ttt_veh_h']
            return data
        base=totals('none');treatment=totals('spread_only')
        deltas={key:treatment[key]-base[key] for key in sorted(set(base)|set(treatment))}
        assert abs(sum(deltas.values())-(arms['spread_only']['parts']['total']-arms['none']['parts']['total']))<1e-8
        results[seed]={'delta_by_address_veh_h':deltas,
            'lane_changes':{arm:{'internal34':sum(a['within_lanes34_changes'].values()),
                                'between_groups':sum(a['between_group_changes'].values())}
                            for arm,a in arms.items()},
            'cells':geometry['cells'],'boundaries':geometry['boundaries']}
    e.save(out/'summary.json',{'results':results,
        'scope':'Post-run2400..2850s component decomposition. No causal mediation claim, no model fitting.',
        'lane_change_scope':'Same-link, same-cell consecutive1s records in FW_E cells5..14 only; lane3<->4 is invisible to the existing lanes3+ group.'})


if __name__=='__main__':
    if '--spatial' in sys.argv:spatial_contrasts()
    else:main()
