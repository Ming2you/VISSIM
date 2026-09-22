"""Compare matched fixed commands and audit conserved transfers after fitting."""
import json
import calibrate as c
from prepare import save,table
from wang_niu import B,O,K,ROOT
ARMS=('none','rm_ramp','vsl','both')


def main():
    actual=c.load(B.parent/'response_chain_20260921/qualification.json')['gains']
    metrics=[];gains=[];checks=[];audits={};flows=[]
    roles=['disabled','receiving_actions','direct_actions','theta15_actions','fixed_theta15_actions']
    if (O/'joint_frozen.json').exists():roles+=['joint_receiving_actions','joint_direct_actions']
    if (O/'hd_wn_joint_no_ctm_actions/refined_guard1_receipt.json').exists():roles+=['joint_no_ctm_actions']
    for role in roles:
        name='hd_wn_'+role;result=c.load(K/('segment_resolution_20260921_cal_'+name)/'result.json')
        role_flows={}
        for arm in ARMS:
            p=c.load(O/name/f'refined_guard1_{arm}.json');old=c.load(B/f'refined_guard1_{arm}.json')
            check=c.screen(p);assert check['passed'];checks.append(dict(case=role,arm=arm,**check))
            for key in ('cells','flows'):assert [r for r in p[key] if r['road']=='FW_W']==[r for r in old[key] if r['road']=='FW_W']
            if role=='disabled':assert p==old
            d=next(x for x in p['diagnostics']['roads'] if x['road']=='FW_E')
            assert d['final_origin_queue_veh']<1e-7
            if role!='disabled':
                a=d['hadiuzzaman_audit'];assert a['max_budget_violation_veh']<1e-7
                audits[role+':'+arm]=a
                if 'direct' not in role:assert a['desired_changed']==0
            if arm=='none':
                for phase,lo,hi in [('train',0,10),('late',10,15)]:metrics.append(dict(case=role,phase=phase,**c.score(p,lo,hi)))
            else:
                delta=result['deltas'][arm]
                gains.append(dict(case=role,arm=arm,actual=actual[arm]['actual']['total'],predicted=delta['total'],
                    mainline=delta['mainline'],on=delta['on'],off=delta['off']))
            f=dict(case=role,arm=arm,merge10490=sum(r['accepted_merge_veh'] for r in p['ramps'] if r['ramp']=='RM_C10490'),
                on10490_ttt=sum(r['connector_ttt_veh_h'] for r in p['ramps'] if r['ramp']=='RM_C10490'),
                origin_requested=d['requested_source_veh'],origin_admitted=d['accepted_source_veh'])
            for key in ('ramp_merges','off_departures','terminal_exits'):
                f[key]=sum(r[key] for r in p['flows'] if r['road']=='FW_E')
            role_flows[arm]=f;flows.append(f)
        for arm in ARMS[1:]:
            row=next(r for r in gains if r['case']==role and r['arm']==arm)
            for k in ('merge10490','on10490_ttt','ramp_merges','off_departures','terminal_exits'):
                row['delta_'+k]=role_flows[arm][k]-role_flows['none'][k]
    for prefix in ('','joint_'):
        if not (O/(prefix+'frozen.json')).exists():continue
        frozen=c.load(O/(prefix+'frozen.json'))
        for key,role in [('receiving','receiving_actions'),('direct_u','direct_actions')]:
            name=frozen[key]['name']
            assert c.load(O/name/'refined_guard1_none.json')==c.load(O/('hd_wn_'+prefix+role)/'refined_guard1_none.json')
    pins=c.load(O/'protocol.json')['source_pins']
    for path,pin in pins.items():
        assert any(p.exists() and c.sha(p)==pin for p in [ROOT/path,O/((ROOT/path).name+'.stage1.txt')]),path
    if (O/'joint_protocol.json').exists():
        for path,pin in c.load(O/'joint_protocol.json')['source_pins'].items():assert c.sha(ROOT/path)==pin,path
    before=c.load(O/'before_sources.json')
    for path,pin in before.items():
        if path.endswith(('parameters.json','canonical_harness.py','/run.py')):assert c.sha(ROOT/path)==pin,path
    # Historical pins remain resolvable after the core/helper edits.
    for name in ('protocol.json','scope_protocol.json'):
        for path,pin in c.load(B/'hadiuzzaman_v1'/name)['source_pins'].items():
            current=ROOT/path
            alternatives=[current,O/(current.name+'.before.txt'),B/'hadiuzzaman_v1'/(current.name+'.all_cells.txt')]
            assert any(p.exists() and c.sha(p)==pin for p in alternatives),path
    for target,rows in [('state_metrics.csv',metrics),('gain_check.csv',gains),('flows.csv',flows),('numerics.csv',checks)]:table(O/target,rows)
    legacy=O/'hd_wn_legacy_receiving/refined_guard1_none.json'
    if legacy.exists():assert c.load(legacy)==c.load(B/'hadiuzzaman_v1/hd_receiving_actions/refined_guard1_none.json')
    receipt=dict(status='IMPLEMENTED_NOT_QUALIFIED',production_adopted=False,new_native_runs=0,
        independent_validation=False,drop_identified=False,source_checks=True,default_exact=4,west_exact=4*len(roles),
        forecast_count=sum(c.load(p)['forecasts'] for p in O.glob('*/refined_guard1_receipt.json')),
        numerics=checks,metrics=metrics,gains=gains,receiving_audits=audits,legacy_hadi_receiving_exact=legacy.exists())
    save(O/'validation.json',receipt)
    print(json.dumps(dict(forecasts=receipt['forecast_count'],metrics=metrics,gains=gains),indent=2))


if __name__=='__main__':main()
