"""Publish evidence and next cause, without adopting an unqualified plant."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
HERE=Path(__file__).resolve().parent;A=HERE.parent
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert not (HERE/'completion.json').exists()
    result=read(HERE/'result.json');run=read(HERE/'launch.json')
    canonical=read(HERE/'canonical2400/assessment.json');balance=read(HERE/'assessment.json')
    assert run['status']=='complete' and run['forecasts']==4
    assert result['disabled_full_response_exact'] and all(canonical['checks'].values())
    assert set(canonical['capacity_changes'])=={'SC6_E_SC104_to_W_SC5','SC6_E_SC104_to_N_SC103'}
    for p,h in result['source_pins'].items():assert sha(p)==h,p
    for name in ('tests.log','regression.log'):assert '\nOK\n' in (HERE/name).read_text(encoding='utf8')
    budget={}
    for arm,row in balance['results'].items():
        available=row['windows'][0]['model_ready_start']+sum(w['model_arrivals_to_ready'] for w in row['windows'])
        native=sum(w['native_through_head_count'] for w in row['windows'])
        budget[arm]=dict(model_max_departure_with_unchanged_arrivals=available,native_through=native,gap=native-available)
        assert native>available+30
    stamp=datetime.now(timezone.utc).isoformat()
    next_step=('343 proved and opt-in repaired SC6 east head attribution: through10200 alone crosses90601-90604; pre-head right10142 must not consume that observed service. '
        '4 isolated forecasts and34tests passed; disabled full response exact. First150 through15.29->22.84 vsnative33; readyat2700 16.15->4.49. '
        'Autonomous through availability6.5+55.025=61.525 over450 is below native97/98, so no further capacity tuning can repair this with fixed arrivals. '
        'Canonical past-only observer replay changes through1965.80->2936.84 and right971.04->fallback206.53, with identical state/demand/other cfg. '
        'Do not call the through-only comparison a fully validated v13 rollout; no production config adoption. '
        'Next separate SC104-to-SC6 current stock, actual upstream service/arrivals and ready transition using existing records and Claude evidence. '
        'Independently qualify pre-head right service/access; do not reuse straight counts or future outflow as its capacity. '
        'City delta still-0.181 vsnative+5.287; RM-vector delta-1.299 vsnative-1.094. '
        'Keep conservation/current route-lane/receiving/FW5/U10/450s/terminalOFF/Omega701; no grid, fresh full optimizer/native or push for the diagnostic step. '
        'Representative/unused-state material gain, production integration/feasible SDMPC choice and same-budget optimizer wall-time remain outstanding.')
    record=dict(status='local_attribution_fixed_full_plant_not_adopted',completed_utc=stamp,
        new_forecasts=4,tests=34,new_native=0,new_optimizer=0,fits=0,production_adopted=False,goal_complete=False,
        deltas=result['deltas'],native_deltas=result['native_deltas'],availability_bound=budget,
        online_observer_capacity_changes=canonical['capacity_changes'],next_step=next_step,
        source_pins={str(p):sha(p) for p in (*HERE.glob('*.py'),HERE/'README.md',HERE/'result.json',
            HERE/'canonical2400/assessment.json',HERE/'head_resources.json',HERE/'config.json')})
    (HERE/'completion.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for p in (A/'plan.json',A.parent/'plan.json'):
        plan=read(p);assert plan['current_stage']=='sc6_shared342_rejected_ready_stock_is_not_local_blocking_queue'
        plan.update(current_stage='sc6_balance343_head_attribution_fixed_arrival_bound_and_right_service_open',
            current_workers=[],latest_stage=str(HERE/'README.md'),next_step=next_step,goal_complete=False,updated_utc=stamp,
            latest_goal_turn=dict(classification='progress',previous_goal_turn='progress342_rejected_blocking_hypothesis_and343_saved_balance_audit',
                evidence='Measured straight-head beta split fixed behind opt-in contract;34tests/4forecasts/canonical causal history replay; finite arrival bound rules out further capacity-only repair.'))
        plan['sc6_balance343']={k:record[k] for k in ('status','completed_utc','new_forecasts','tests','deltas','production_adopted','goal_complete')}
        p.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for p,link in ((A/'README.md','sc6_balance343/README.md'),(A.parent/'README.md','aggregate270/sc6_balance343/README.md')):
        text=p.read_text(encoding='utf8')
        text='最新 진행: [SC6 직진 head 귀속·도착량 상한343]('+link+'). 국소 오류 확인/수정; 도시 손익 방향과 전체 운영 통합은 미완료.\n\n'+text
        p.write_text(text,encoding='utf8')
    print(json.dumps({k:record[k] for k in ('status','new_forecasts','tests','availability_bound','goal_complete')},indent=2))
if __name__=='__main__':main()
