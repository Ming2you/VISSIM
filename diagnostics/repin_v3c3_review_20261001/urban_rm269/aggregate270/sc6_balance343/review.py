"""Assess the single head-attribution change against held native targets."""
from pathlib import Path
import gzip,hashlib,json
HERE=Path(__file__).resolve().parent;A=HERE.parent
THROUGH='SC6_E_SC104_to_W_SC5';RIGHT='SC6_E_SC104_to_N_SC103'
def read(p):
    p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def main():
    out=HERE/'forecast2400';report=read(out/'summary.json');assert report['status']=='complete' and report['forecasts']==4
    assert not (HERE/'result.json').exists()
    for p,h in report['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    disabled=read(out/'disabled_hold.response.json.gz')
    old=read(Path('E:/VISSIM_analysis/20261010_native_routes329/forecast2400/hold.response.json.gz'))
    assert disabled==old,'Disabled full response changed'
    native=read(HERE/'assessment.json');gain=read(A/'gain_account341/assessment.json')
    rows={}
    for arm in ('hold','city','joint'):
        r=read(out/(arm+'.response.json.gz'));resources={(x['resource'],x['start_sec'],x['kind']):x for x in r['resource_allocations']}
        bins=[]
        for start in (2400,2550,2700):
            ticks=range(start,start+150,10)
            flow=sum(resources[THROUGH,t,'urban_movement_intended_limit']['accepted_total_veh'] for t in ticks)
            end=resources[THROUGH,start+140,'urban_movement_stock']['available_veh']-resources[THROUGH,start+140,'urban_movement_intended_limit']['accepted_total_veh']
            bins.append(dict(start=start,through=flow,ready_end=end,
                right=sum(resources[RIGHT,t,'urban_movement_intended_limit']['accepted_total_veh'] for t in ticks)))
        rows[arm]=dict(omega=report['results'][arm]['omega_ttt_veh_h'],bins=bins,
            shared_feasible=report['results'][arm]['shared_constraints']['feasible'],
            wall_sec=report['results'][arm]['wall_sec'])
    deltas={'city_minus_hold':rows['city']['omega']-rows['hold']['omega'],
            'joint_minus_city':rows['joint']['omega']-rows['city']['omega']}
    # Preserve the existing evaluator's contrast names instead of guessing them.
    native_deltas={k:v['native'] for k,v in gain['contrasts'].items()}
    value=dict(status='complete_single_head_attribution_diagnostic',results=rows,deltas=deltas,
        native_deltas=native_deltas,disabled_full_response_exact=True,forecasts=4,
        tests=6,regression_tests=28,optimizer=0,native=0,coefficient_fits=0,
        full_online_observer_replay=False,production_adopted=False,goal_complete=False,
        scope='Physical head mapping fixed under opt-in v13. Forecast changes only the through cap using completed past head pairs. Right rate is retained, not newly qualified.',
        native_head_bins={arm:[w['native_through_head_count'] for w in v['windows']] for arm,v in native['results'].items()},
        native_terminal_through={arm:[w['terminal_through'] for w in v['native_snapshots']] for arm,v in native['results'].items()},
        limitations=['No native/optimizer wall-time result from scalar endpoint timing.',
            'Native future counts are validation only.',
            'Source arrivals and local stopped/ready placement are not repaired by assigning the correct head rate.',
            'The configured online observer must be replayed separately; this controlled experiment preserves the old right service to isolate the through mapping.'],
        source_pins={**report['source_pins'],**{str(p):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__),HERE/'assessment.json',HERE/'regression.log',out/'summary.json',A/'gain_account341/assessment.json')}})
    (HERE/'result.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:value[k] for k in ('results','deltas','native_deltas','disabled_full_response_exact')},indent=2))
if __name__=='__main__':main()
