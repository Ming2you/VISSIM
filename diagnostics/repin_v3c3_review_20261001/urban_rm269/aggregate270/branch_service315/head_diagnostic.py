"""Conditional saved-response diagnosis; not another autonomous prediction."""
from collections import Counter
from pathlib import Path
import gzip,hashlib,json

HERE=Path(__file__).resolve().parent
OUT=Path('E:/VISSIM_analysis/20261010_branch_service315/forecast2400')
PAST=Path('E:/VISSIM_analysis/20261010_sc107_composition312')


def main():
    dest=HERE/'head_service_diagnostic.json';assert not dest.exists()
    done=json.loads((PAST/'retained_completion.json').read_bytes())
    raw=Path(done['cache']).read_bytes();assert hashlib.sha256(raw).hexdigest()==done['cache_sha256']
    past=json.loads(gzip.decompress(raw))
    counts=Counter((r['source'],r['head_lane'],r['sg'],r['turn']) for r in past['witnesses'])
    for lane in (2,3,4):
        assert counts['SC1004',lane,'2','through']>0
        assert counts['SC1005',lane,'2','through']>0
    names=('SC107_W_SC1004_to_E_SC108','SC107_W_SC1005_to_E_SC108')
    rates={names[0]:820.416125984499,names[1]:1168.976081919719}
    # Rates verified from the pinned baseline configuration, never fitted here.
    import pickle
    initial=HERE.parent/'citysplit287/forecast2400/initial.pickle'
    cfg,_,_=pickle.loads(initial.read_bytes())
    for m,rate in rates.items():
        assert cfg.network.movement_capacity_by_movement_veh_h[m]==rate
        assert cfg.network.urban_movements[m]['phase']=='SC107_p3'
        assert cfg.network.urban_movements[m]['receiving_link']=='SC107_to_SC108'
    result={};pins={str(initial):hashlib.sha256(initial.read_bytes()).hexdigest(),
                   done['cache']:done['cache_sha256']}
    for arm in ('hold','city'):
        path=OUT/(arm+'.response.json.gz');raw=path.read_bytes();pins[str(path)]=hashlib.sha256(raw).hexdigest()
        data=json.loads(gzip.decompress(raw))
        rows={(x['start_sec'],x['resource'],x['kind']):x for x in data['resource_allocations'] if x['resource'] in rates}
        opportunities=[]
        for t in range(2400,2850,10):
            a=rows[t,names[0],'urban_movement_stock'];lim=rows[t,names[0],'urban_movement_intended_limit'];b=rows[t,names[1],'urban_movement_stock']
            if (lim['accepted_total_veh']>0 and a['available_veh']>lim['available_veh']+1e-7
                    and abs(lim['available_veh']-lim['accepted_total_veh'])<1e-7):
                implied_green_h=lim['available_veh']/rates[names[0]]
                spare=max(0.,rates[names[1]]*implied_green_h-b['accepted_total_veh'])
                potential=min(a['available_veh']-a['accepted_total_veh'],spare)
                if potential>1e-7:
                    opportunities.append(dict(start_sec=t,source104_ready=a['available_veh'],source105_ready=b['available_veh'],
                        original104_accept=a['accepted_total_veh'],original105_accept=b['accepted_total_veh'],
                        inferred105_unused_service=spare,conditional_single_step_opportunity=potential))
        result[arm]=opportunities
    output=dict(status='shared_head_source_partition_needs_autonomous_test',source_pins=pins,
        known_past_common_lanes=[2,3,4],head_counts=[dict(source=k[0],lane=k[1],sg=k[2],turn=k[3],count=v) for k,v in counts.items()],
        movement_rates_veh_h=rates,intervals=result,
        limits=['Individual-step opportunities condition on saved future states. Their sum is not an autonomous discharge or TTT benefit.',
                'Common head/lane use establishes overlap, not instantaneous lateral access or strictFIFO equivalence.',
                'Keep source/route tags, actual receiver limits and total shared capacity if testing a common service group.',
                'Current-queue-only313 partition remains rejected. Do not assign future observed head labels to initial vehicles.'])
    dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('COMMON_LANES',output['known_past_common_lanes'],'CONDITIONAL_INTERVALS',{k:len(v) for k,v in result.items()})


if __name__=='__main__':main()
