"""Reuse closed counters and model ledgers to separate W_out supply and clearing.

No FZP scan, model rollout, rate fitting or native execution. Unknown city inflow
minus free-tail outflow is explicitly a net residual, never either gross flow.
"""
import ctypes,gzip,hashlib,json,math,sys,xml.etree.ElementTree as ET
from collections import Counter,defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(ROOT),str(H)]
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_observation import check_rule_crosscheck
from evaluation.controllers.route_choice_corridor import _known_classify
from qualify_native2400 import validate_scope
PINS={};RUNS=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29')
W={68,121,10772,10625,10629,10633};KEY='storage:SC1004_W_out'
def read(p,compressed=False):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return json.loads(gzip.decompress(b) if compressed else b)
def static_id(value):
    assert type(value) in (int,float) and math.isfinite(value) and value>0 and float(value).is_integer()
    return int(value)
def frame_summary(frame,spec):
    assert frame['complete'];selected=[r for r in frame['vehicles'] if r[1] in W]
    tags=Counter();stopped=Counter();lanes=Counter()
    for r in selected:
        static=r[8]=='STATIC'
        target=_known_classify(dict(link_no=r[1],position_m=r[3]),dict(route_decision_no=static_id(r[6]) if static else r[6],route_no=static_id(r[7]) if static else r[7],route_decision_type=r[8]),spec)
        tags[target]+=1;lanes[f'{r[1]}:{r[2]}']+=1
        if r[4]<5:stopped[target]+=1
    return dict(total=len(selected),route_targets=dict(tags),speed_below5_kph=dict(stopped),lanes=dict(lanes))
def main():
    out=HERE/'assessment_integer_ids.json';assert not out.exists()
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
    validate_scope(read(H/'native2400_analysis/summary.json'),read(H/'native2400_analysis/observed_input_qualification.json'))
    closure=read(H/'native2400_analysis/runtime_closure.json');assert closure['all_owned_processes_closed'] and closure['owner_exit_code']==0
    folder=H/'sc1_supply/forecast2400';net=read(folder/'network.json');state=read(folder/'state.json');spec=net['known_legsplit_routes']
    # Reconcile the physical full path, including empty-at-initial10772.
    assert {int(r['link']) for path in spec['physical_travel']['destinations'].values() for r in path}=={68,121,10772}
    assert {int(x) for x in spec['prechoice_connectors']}=={10625,10629,10633}
    network=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    b=network.read_bytes();PINS[str(network)]=hashlib.sha256(b).hexdigest();tree=ET.fromstring(b)
    links={r.get('no'):r for r in tree.findall('./links/link')}
    assert all(int(v.get('link')) not in W for v in tree.findall('./vehicleInputs/vehicleInput'))
    assert links['10682'].find('toLinkEndPt').get('lane').split()[0]=='121'
    assert links['10773'].find('fromLinkEndPt').get('lane').split()[0]=='121'
    arms={}
    for arm in ('hold','selected'):
        native=[];path=RUNS/arm/f'decisions_sdmpc31_g_2400_{arm}_s29'
        for end in (2550,2700,2850):
            raw=read(path/f'state_{end:06d}.json');bundle=oc.load_bundle(raw);obs=bundle.obs
            ds,_=oc.read_detector_csv(obs['detector_config']['path'],obs['detector_config']['sha256'])
            for p in (Path(obs['detector_config']['path']),path/obs['mer']['chunk'],path/obs['err']['chunk']):
                PINS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
            oc.validate_raw(obs,ds,expected_simres=10);check_rule_crosscheck(obs,ds)
            boundary=oc.evaluate_boundaries(obs,ds,bundle.frame_end,bundle.frame_start,bundle.err_rows)
            removed=oc.window_removals(bundle.err_rows,end-150,end)
            count=lambda frame,link:sum(r[1]==link for r in frame['vehicles'])
            n0,n1=frame_summary(bundle.frame_start,spec),frame_summary(bundle.frame_end,spec)
            if end==2550:
                expected=Counter()
                for c in state['known_legsplit_route_state']['cohorts']:expected[c['target']]+=c['vehicles']
                assert n0['route_targets']==dict(expected),'Native integer route identities must match the initialized model groups'
            rm={r:boundary['ramp_arrival:'+r].cross for r in ('RM_C10681','RM_C10646')}
            # Off-entry is at the connector start after native stock correction.
            direct=boundary['off_entry:10682'].cross+count(bundle.frame_start,10682)-count(bundle.frame_end,10682)-sum(r['link']==10682 for r in removed)
            assert direct>=0
            deleted=sum(r['link'] in W for r in removed)
            net_city_minus_free=n1['total']-n0['total']+sum(rm.values())+deleted-direct
            heads={label:sum(boundary[d.boundary_ref].cross for d in ds if d.role=='head' and d.link==link and d.lane in lanes)
                   for label,link,lanes in [('from52',52,{1,2,3}),('from66',66,{4})]}
            native.append(dict(start_sec=end-150,initial=n0,final=n1,ramps=rm,direct_off10682_out=direct,
                removals=deleted,net_city_in_minus_free_out=net_city_minus_free,upstream_head_proxy=heads,
                not_gross_city_arrival_or_free_exit=True))
        response=read(folder/(arm+'.response.json.gz'),True)
        residence={r['end_sec']:r['model_stock_veh'] for r in response['residence'] if r['stage']=='urban'}
        bins={t:[] for t in (2400,2550,2700)}
        for r in response['transfers']:
            t=2400+150*int((r['start_sec']-2400)//150)
            if r['source']==KEY or r['target']==KEY:bins[t].append(r)
        rows=[]
        for j,t in enumerate(bins):
            before=net['urban_link_storage_veh']['SC1004_W_out']-state['urban_link_storage']['SC1004_W_out'] if j==0 else residence[t][KEY]
            after=residence[t+150][KEY];incoming=Counter();outgoing=Counter()
            for r in bins[t]:
                if r['source']==r['target']:continue
                if r['target']==KEY:incoming[r['source'] or r['route_key']]+=r['vehicles']
                if r['source']==KEY:outgoing[r['target'] or r['route_key']]+=r['vehicles']
            assert abs(before+sum(incoming.values())-sum(outgoing.values())-after)<1e-7
            known_rm={r:outgoing.get('ramp:'+r,0.) for r in ('RM_C10681','RM_C10646')}
            # Keep all source labels rather than assuming an observed head is
            # already at the W_out entrance plane.
            rows.append(dict(start_sec=t,initial=before,final=after,incoming_by_source=dict(incoming),outgoing_by_target=dict(outgoing),
                ramps=known_rm,native=native[j]))
        arms[arm]=rows;del response
    PINS[str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for p in (H.parent/'upstream_worklog/02_urban_b2/diag_c3/C3_DIAGNOSIS.md',H.parent/'upstream_worklog/02_urban_b2/impl/STAGE3.md'):
        PINS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    result=dict(status='complete_boundary_balance_diagnostic',arms=arms,new_rollouts=0,new_native=0,raw_fzp_scans=0,coefficients_fitted=0,
        full_physical_domain=sorted(W),model_baseline='sc1_supply',source_pins=PINS,
        limitations=['Native residual is city inflow minus free exit, not separate gross flows.',
            'Upstream52/66 heads are proxies offset from connector entries;46 right branches before its head.',
            'Current route tags identify current chosen destinations; prechoice and unknown are kept.',
            '10772 added for path completeness; initial-support cost map did not include it.',
            'No future observations enter any prediction; no isolatedRM causal claim.'])
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for arm,rows in arms.items():
        for r in rows:print(arm,r['start_sec'],'stock',r['final'],r['native']['final']['total'],'model_in',r['incoming_by_source'],'model_out',r['outgoing_by_target'],'native_net',r['native']['net_city_in_minus_free_out'],'rm',r['ramps'],r['native']['ramps'],flush=True)
if __name__=='__main__':main()
