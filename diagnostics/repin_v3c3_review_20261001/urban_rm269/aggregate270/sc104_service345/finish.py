"""Publish the completed diagnostic and preserve the full unresolved goal."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
HERE=Path(__file__).resolve().parent;A=HERE.parent
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert not (HERE/'completion.json').exists()
    r=read(HERE/'result.json');launch=read(HERE/'launch_v2.json')
    assert launch['status']=='complete' and launch['forecasts']==5 and r['default_full_response_exact']
    assert read(HERE/'forecast2400_v2/runtime_clock_check.json')['checks']==60
    assert all(x['feasible'] and x['conservation_states']==4 for x in r['rows'].values())
    for p,h in r['source_pins'].items():assert sha(p)==h,p
    assert 'OK' in (HERE/'tests.log').read_text(encoding='utf8')
    stamp=datetime.now(timezone.utc).isoformat()
    step=('344 native input1032 single route1095:1 corrects false SC104 beta split; cap masks flow. '
        '345 past-only actual head/LDP corrects straight-only monitor clock and lower observed service826.12->2828.57; '
        'source inflow53.01->107.70 vsnative140. 11tests+60 actual10s-clock bins, conservation/receiving/NP/NUF/3-block writer passed. '
        'V1 diagnostic static-cache miss preserved; v2 targeted refresh proved runtime application. '
        'City delta remains-.178 vsnative+5.287; whole-RM-vector delta-1.299 vsnative-1.094. Do not tune common input harder to fit a control contrast. '
        'Next reuse existing boundary cache: normal exit from1210018302 falls33 (+2.389vehh), appearances on74 rise42 (+1.741vehh); '
        'check Claude first and separate native insertion/sampling ambiguity, receiving and model flow before changing mechanisms. '
        'SC6 prehead right service remains unqualified; no operating config adoption. '
        'Preserve current routes/lane, conservation, receiving, same demand/Omega701,FW5/U10,450s/terminalOFF. '
        'No new full optimizer/native/grid/push in diagnostic step. Production integration, unused-state/10681 material gain, feasible SDMPC choice and same-budget wall verification remain.')
    record=dict(status='source_clock_service_diagnostic_complete_city_direction_open',completed_utc=stamp,
        new_forecasts=10,qualified_forecasts=5,route_only_previous_forecasts=4,tests=11,runtime_clock_bins=60,
        native_runs=0,optimizer_runs=0,coefficient_fits=0,production_adopted=False,goal_complete=False,
        deltas=r['deltas'],next_step=step,
        source_pins={str(p):sha(p) for p in (*HERE.glob('*.py'),HERE/'README.md',HERE/'result.json',HERE/'past_head.json',HERE/'prefix.json')})
    (HERE/'completion.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for p in (A/'plan.json',A.parent/'plan.json'):
        plan=read(p)
        assert plan['current_stage']=='sc6_balance343_head_attribution_fixed_arrival_bound_and_right_service_open'
        plan.update(current_stage='sc104_service345_past_clock_and_arrival_improved_city_direction_open',current_workers=[],
            latest_stage=str(HERE/'README.md'),next_step=step,goal_complete=False,updated_utc=stamp,
            latest_goal_turn=dict(classification='progress',previous_goal_turn='progress344_route_false_split_and_service_bound_identified',
                evidence='Past native head/SG proof; model runtime clock corrected; source flow gap reduced; city gain unchanged; next major boundary differences located.'))
        plan['sc104_service345']={k:record[k] for k in ('status','completed_utc','new_forecasts','qualified_forecasts','tests','deltas','production_adopted','goal_complete')}
        p.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for p,link in ((A/'README.md','sc104_service345/README.md'),(A.parent/'README.md','aggregate270/sc104_service345/README.md')):
        p.write_text('최신 진행: [SC104 직진 신호·서비스345]('+link+'). 유입 과소예측 감소, 도시 제어 손익 방향 및 운영 통합은 미완료.\n\n'+p.read_text(encoding='utf8'),encoding='utf8')
    print(json.dumps({k:record[k] for k in ('status','qualified_forecasts','tests','runtime_clock_bins','deltas','goal_complete')},indent=2))
if __name__=='__main__':main()
