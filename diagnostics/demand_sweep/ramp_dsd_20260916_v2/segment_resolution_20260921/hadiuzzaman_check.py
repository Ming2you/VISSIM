"""Post-fit matched-command validation and physical layout review; no native run."""
import json,math,xml.etree.ElementTree as ET
from pathlib import Path
import calibrate as c
from prepare import save,table
B=c.B;O=B/'hadiuzzaman_v1';K=B.parent/'cohort_dynamics_20260920';ROOT=c.ROOT

def main():
    actual=c.load(B.parent/'response_chain_20260921/qualification.json')['gains']
    metrics=[];gains=[];audits={};checks=[]
    roles=['disabled','receiving_actions','hybrid_actions','paper_switch_actions','theta15_sensitivity',
           'scope_12_35_17','scope_actions','theta15_receiving','final_disabled']
    for role in roles:
        name='hd_'+role;result=c.load(K/('segment_resolution_20260921_cal_'+name)/'result.json')
        spec=c.load(O/(name+'.json'))
        for arm in ('none','rm_ramp','vsl','both'):
            p=c.load(O/name/f'refined_guard1_{arm}.json');base=c.load(B/f'refined_guard1_{arm}.json')
            check=c.screen(p);checks.append(dict(case=role,arm=arm,**check))
            for key in ('cells','flows'):assert [r for r in p[key] if r['road']=='FW_W']==[r for r in base[key] if r['road']=='FW_W']
            if role.endswith('disabled'):assert p==base
            details=next(d for d in p['diagnostics']['roads'] if d['road']=='FW_E')
            if not role.endswith('disabled'):
                audit=details['hadiuzzaman_audit'];audits[role+':'+arm]=audit
                assert audit['receiving_steps']>0 and audit['max_budget_violation_veh']<1e-7
                if spec['hadiuzzaman']['relaxation']=='fd_cap':assert audit['desired_changed']==0
                else:
                    if spec['hadiuzzaman']['relaxation']=='command' or arm in ('vsl','both'):assert audit['desired_changed']>0
                assert abs(details['final_origin_queue_veh'])<1e-7,'New uncounted external source backlog'
            if arm=='none':
                for phase,lo,hi in [('train',0,10),('late',10,15)]:metrics.append(dict(case=role,phase=phase,**c.score(p,lo,hi)))
            else:
                delta=result['deltas'][arm]
                gains.append(dict(case=role,arm=arm,actual=actual[arm]['actual']['total'],predicted=delta['total'],
                    mainline=delta['mainline'],on=delta['on'],off=delta['off'],numerical_pass=check['passed'],
                    model_comparison_only=role not in ('paper_switch_actions','theta15_sensitivity','theta15_receiving')))
    frozen=c.load(O/'selected_hybrid.json')
    assert c.load(O/frozen['name']/'refined_guard1_none.json')==c.load(O/'hd_hybrid_actions/refined_guard1_none.json')
    scope=c.load(O/'scope_selected.json')
    assert c.load(O/scope['name']/'refined_guard1_none.json')==c.load(O/'hd_scope_actions/refined_guard1_none.json')
    for name in ('protocol.json','scope_protocol.json'):
        for path,pin in c.load(O/name)['source_pins'].items():
            candidates=[ROOT/path,O/((ROOT/path).name+'.all_cells.txt')]
            assert any(p.exists() and c.sha(p)==pin for p in candidates),path
    equivalence=[]
    for arm in ('vsl','both'):
        switched=c.load(O/'hd_paper_switch_actions'/f'refined_guard1_{arm}.json')
        common=c.load(O/'hd_scope_12_35_17'/f'refined_guard1_{arm}.json')
        for key in ('cells','flows','lane_groups','ramps','ports'):
            assert switched[key]==common[key],(arm,key,'Controlled traffic must be identical')
        equivalence.append(arm)
    assert c.sha(ROOT/'evaluation/parameters.json')==c.load(O/'before_sources.json')['evaluation/parameters.json']
    # Draw Fig4-style bounds from actual chain geometry. Do not claim a native
    # DSD location/coverage has been changed by this geometric calculation.
    geo=c.G;layout=[];speed=120/3.6;critical=speed*2.5+speed**2/(2*1.5)
    ports=[p for p in geo['boundaries'] if p['road']=='FW_E' and p['kind'] in ('ramp','offramp')]
    for connector in (10643,10490):
        pos=next(p['chain_pos_m'] for p in ports if p['connector']==connector)
        layout.append(dict(connector=connector,bottleneck_m=pos,critical_start_m=pos-600-critical,
            critical_end_m=pos-600,discharge_start_m=pos-600,discharge_end_m=pos,
            ports_within_discharge=[p['connector'] for p in ports if pos-600<p['chain_pos_m']<pos]))
    protocol=c.load(K/'segment_resolution_20260921_cal_hd_disabled/protocol.json')
    network=next(ROOT/p for p in protocol['source_pins'] if p.lower().endswith('.inpx'))
    root=ET.parse(network).getroot();chain={p['link']:p['offset_m'] for p in geo['chains']['FW_E']}
    dsds=[]
    for d in root.iter('desSpeedDecision'):
        if 51<=int(d.attrib['no'])<=58:
            link=int(d.attrib['lane'].split()[0]);pos=float(d.attrib['pos'])
            dsds.append(dict(id=int(d.attrib['no']),link=link,position_m=pos,chain_m=chain.get(link,0)+pos if link in chain else None))
    save(O/'spatial_layout.json',dict(nominal_speed_kmh=120,reaction_sec=2.5,deceleration_m_s2=1.5,
        stopping_length_m=critical,discharge_length_m=600,geometric_proposals=layout,existing_target_dsds=dsds,
        native_network_modified=False,network_sha256=c.sha(network)))
    table(O/'state_metrics.csv',metrics);table(O/'gain_check.csv',gains);table(O/'numerics.csv',checks)
    save(O/'validation.json',dict(state_metrics=metrics,gains=gains,numerics=checks,executed=audits,
        default_exact=4,west_exact=4*len(roles),selected=c.load(O/'selected.json'),selected_hybrid=frozen,selected_scoped=scope,
        controlled_switch_common_traffic_exact=equivalence,status='IMPLEMENTED_NOT_QUALIFIED',
        forecast_count=sum(c.load(p)['forecasts'] for p in O.glob('*/refined_guard1_receipt.json')),
        source_checks=True,production_adopted=False,new_native_runs=0,drop_identified=False,independent_validation=False))
    print(json.dumps(dict(metrics=metrics,gains=gains,layout=layout,dsds=dsds),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
