"""SC16 source head witness from closed counters; no FZP/native/forecast."""
import gzip,hashlib,json,pickle,sys,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];H=HERE.parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.control_area_objective import get_ledger
BASE=HERE.parent/'matched280/authority'
NATIVE=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29')
pins={}
def read(p):
    p=Path(p);data=p.read_bytes();pins[str(p)]=hashlib.sha256(data).hexdigest();return json.loads(data)


def main():
    target=HERE/'supply.json';assert not target.exists()
    cfg,state,_=pickle.loads((BASE/'initial.pickle').read_bytes())
    specs=cfg.network.urban_movements
    movements=[m for m,s in specs.items() if m.startswith('SC16_S_') and s['phase']=='SC16_p1']
    assert len(movements)==4
    net=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    tree=ET.parse(net)
    heads={h.get('no'):h for h in tree.findall('./signalHeads/signalHead') if h.get('lane').split()[0]=='1210009503' and h.get('sg')=='16 8'}
    assert set(heads)=={'180801','180802','180803'}
    links={l.get('no'):l for l in tree.findall('./links/link')}
    # The right turn is downstream of the head and shares lane1; compare
    # through+right together, never call this an observed connector count.
    for c in ('10249','10253'):
        f=links[c].find('fromLinkEndPt');assert f.get('lane')=='1210009503 1'
        assert float(f.get('pos'))>max(float(h.get('pos')) for h in heads.values())
    report={}
    for arm in ('hold','selected'):
        folder=NATIVE/arm/f'decisions_sdmpc31_g_2400_{arm}_s29'
        raw=json.loads(gzip.decompress((BASE/(arm+'.response.json.gz')).read_bytes()))
        records={(r['resource'],r['start_sec'],r['kind']):r for r in raw['resource_allocations'] if r['kind'] in ('urban_movement_stock','urban_movement_intended_limit')}
        arms=[]
        for end in (2550,2700,2850):
            snapshot=read(folder/f'state_{end:06}.json');bundle=oc.load_bundle(snapshot)
            detectors,_=oc.read_detector_csv(bundle.obs['detector_config']['path'],bundle.obs['detector_config']['sha256'])
            oc.validate_raw(bundle.obs,detectors,expected_simres=10)
            bounds=oc.evaluate_boundaries(bundle.obs,detectors,bundle.frame_end,bundle.frame_start,bundle.err_rows)
            selected=[d for d in detectors if d.role=='head' and d.ref.split('|')[0] in heads]
            assert len(selected)==3
            native=sum(bounds[d.boundary_ref].cross for d in selected)
            count={}
            for m in movements:
                rr=[r for r in raw['resource_allocations'] if r['kind']=='urban_movement_intended_limit' and r['resource']==m and end-150<=r['start_sec']<end]
                positive=[r for r in rr if r['available_veh']>0]
                count[m]=dict(accepted=sum(r['accepted_total_veh'] for r in rr),receiving_rejected=sum(r['available_veh']-r['accepted_total_veh'] for r in rr),
                    positive_requests=len(positive),requests_consuming_all_ready=sum(abs(r['available_veh']-records[m,r['start_sec'],'urban_movement_stock']['available_veh'])<1e-7 for r in positive))
            incoming={}
            for row in raw['transfers']:
                if row['target']=='storage:SC16_to_SC12' and row['source']!=row['target'] and end-150<=row['start_sec']<end:
                    key=row['source'] or 'exogenous';incoming[key]=incoming.get(key,0)+row['vehicles']
            arms.append(dict(start=end-150,native_south_through_right_heads=native,model_south_through_right=sum(x['accepted'] for x in count.values()),
                by_movement=count,all_model_sources_to_sc12=incoming))
            for p in (folder/bundle.obs['mer']['chunk'],Path(bundle.obs['detector_config']['path'])):
                pins[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
        report[arm]=arms
    stocks=get_ledger(state).stocks
    detail={m:dict(spec=specs[m],rate=cfg.network.movement_capacity_by_movement_veh_h[m],initial=stocks.get('movement:'+m)) for m in movements}
    pools=getattr(cfg.network,'local_service_pool',{})
    for m in movements:detail[m]['pool']=pools.get('group_of',{}).get(m)
    for p in (Path(__file__),BASE/'initial.pickle',BASE/'summary.json',net,ROOT/'evaluation/controllers/obs150_contract.py'):
        pins[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    result=dict(status='closed_source_head_comparison',arms=report,model_initial=detail,
        limitations=['Head count combines through and right because they share a downstream branch; not an exact SC16toSC12 connector count.',
                     'No future observations substituted into forecasts. Comparing same saved actual command windows.',
                     'Receiving rejection zero cannot distinguish upstream arrival timing from insufficient service by itself.'],
        new_forecasts=0,new_native=0,fzp_scans=0,source_pins=pins)
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print('INITIAL', {k:{q:v[q] for q in ('rate','initial','pool')} for k,v in detail.items()})
    for a,rows in report.items():
        for r in rows:print(a,r)


if __name__=='__main__':main()
