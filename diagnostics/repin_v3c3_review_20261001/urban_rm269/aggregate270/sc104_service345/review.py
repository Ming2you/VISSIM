"""Review actual runtime clock and autonomous arrivals, not coefficient fit."""
from pathlib import Path
from collections import defaultdict
import gzip,hashlib,json,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
def read(p):
    p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def main():
    assert not (HERE/'result.json').exists()
    out=HERE/'forecast2400_v2';s=read(out/'summary.json');assert s['status']=='complete' and s['forecasts']==5
    assert read(out/'runtime_clock_check.json')['passed']
    for p,h in s['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    assert read(out/'disabled_hold.response.json.gz')==read(A/'sc6_balance343/forecast2400/hold.response.json.gz')
    rows={}
    for arm in ('disabled_hold','clock_hold','hold','city','joint'):
        r=read(out/(arm+'.response.json.gz'));rs=r['resource_allocations'];flows={}
        for m in ('SC104_E_to_W_SC6','SC6_E_SC104_to_W_SC5','SC6_E_SC104_to_N_SC103'):
            q=[x for x in rs if x['resource']==m and x['kind']=='urban_movement_intended_limit']
            flows[m]=dict(departure=sum(x['accepted_total_veh'] for x in q),
                bins=[sum(x['accepted_total_veh'] for x in q if t<=x['start_sec']<t+150) for t in (2400,2550,2700)])
        rows[arm]=dict(omega=s['results'][arm]['omega_ttt_veh_h'],flows=flows,
            feasible=s['results'][arm]['shared_constraints']['feasible'],wall=s['results'][arm]['wall_sec'],
            conservation_states=s['results'][arm]['conservation_states'])
    old=read(A/'sc104_arrival344/result.json');gain=read(A/'gain_account341/assessment.json')
    deltas=dict(city_minus_hold=rows['city']['omega']-rows['hold']['omega'],joint_minus_city=rows['joint']['omega']-rows['city']['omega'])
    # Existing cache only: locate where appearance/exit timing differs. These
    # are diagnostics, not exogenous input matching or new native performance.
    grouped={}
    root=ET.parse(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx').getroot()
    input_links={v.get('link') for v in root.findall('./vehicleInputs/vehicleInput')}
    for arm in ('hold','city'):
        g=defaultdict(lambda:dict(count=0,cost=0.))
        c=read(Path('E:/VISSIM_analysis/20261010_exit_timing309')/(arm+'.json.gz'))
        for e in c['events']:
            if not 2400<=e['mid_sec']<2850:continue
            if e['kind'] not in ('appeared_or_reappeared_inside','observed_exit'):continue
            key=(e['kind'],str(e['to_link'] if e['kind']=='appeared_or_reappeared_inside' else e['from_link']))
            g[key]['count']+=1;g[key]['cost']+=(2850-e['mid_sec'])/3600*(1 if e['kind']=='appeared_or_reappeared_inside' else -1)
        grouped[arm]=g
    attribution=[]
    for key in grouped['hold'].keys()|grouped['city'].keys():
        h=grouped['hold'].get(key,dict(count=0,cost=0));c=grouped['city'].get(key,dict(count=0,cost=0))
        attribution.append(dict(kind=key[0],link=key[1],delta_count=c['count']-h['count'],delta_cost=c['cost']-h['cost'],native_input_link=key[1] in input_links))
    attribution.sort(key=lambda x:abs(x['delta_cost']),reverse=True)
    result=dict(status='past_only_source_service_and_clock_qualified_local_forecast',rows=rows,deltas=deltas,
        native_deltas={k:v['native'] for k,v in gain['contrasts'].items()},
        native_incoming=old['native_incoming'],default_full_response_exact=True,runtime_past_clock_bins=60,
        new_forecasts=10,qualified_forecasts=5,initial_clock_install_failure_preserved=True,
        tests=11,native=0,optimizer=0,fits=0,production_adopted=False,goal_complete=False,
        native_appearance_exit_attribution=attribution,
        source_pins={**s['source_pins'],str(out/'summary.json'):hashlib.sha256((out/'summary.json').read_bytes()).hexdigest()},
        limitations=['Rate is conservative observed green throughput, not saturation identification.',
            'SC6 right service remains the older unqualified rate in this isolated diagnostic.',
            'City loss direction remains wrong; do not increase the common source rate to fit a contrast.',
            'Joint-minus-city changes the whole RM vector, not only10681.',
            'Appearances at an input link may include sampling ambiguity; not proven insertions.',
            'Scalar endpoint wall is not AD, optimizer or native runtime performance.'])
    (HERE/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(rows=rows,deltas=deltas,native_deltas=result['native_deltas'],top_native_events=attribution[:8]),indent=2))
if __name__=='__main__':main()
