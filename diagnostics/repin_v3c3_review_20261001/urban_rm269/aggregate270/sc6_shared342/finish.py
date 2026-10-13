"""Record a failed bounded hypothesis without claiming full-goal completion."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
HERE=Path(__file__).resolve().parent;A=HERE.parent
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert not (HERE/'completion.json').exists()
    data=read(HERE/'assessment.json');run=read(HERE/'launch.json')
    assert run['status']=='complete' and run['forecasts']==4
    assert data['status']=='rejected_no_generalization_forecasts' and data['disabled_full_response_exact']
    assert all(sha(p)==h for p,h in data['source_pins'].items())
    prior=read(A/'gain_account341/assessment.json')
    for k,value in data['native_delta_omega'].items():assert abs(value-prior['contrasts'][k]['native'])<1e-8
    proof={}
    for arm,rows in data['native_lane_validation'].items():
        history=read(HERE/'forecast2400'/f'{arm}.gate.json')['history'];proof[arm]=[]
        for row in rows:
            total=sum(v for k,v in row['all_vehicle_lane_route'].items() if k.endswith('next10200.0'))
            stopped=sum(v for k,v in row['contiguous_lane_route'].items() if k.endswith('next10200.0'))
            if row['sec']==2400:ready=6.5
            else:
                tick=next(r for r in history if r['step']*10==row['sec']-10)
                ready=tick['through_queue']-tick['through_accepted']
            proof[arm].append(dict(sec=row['sec'],native_source_all_through=total,native_head_ready_through=stopped,
                model_movement_ready_through=ready,native_lane1=row['observed_lane1_through_front'],model_lane1=row['model_lane1_through_queue']))
    stamp=datetime.now(timezone.utc).isoformat()
    step=('342 shared-prehead candidate was rejected after4forecasts; no followup3300 forecasts or adoption. '
          'Direct SG authority mismatch is real, but assigning the aggregate through-ready queue to a local stopped lane prolongs blockage. '
          'At2700 native source contains2through vehicles; model ready16.15hold/10.14city, lane labels3.91/2.46 versus actual1/0. '
          'Do not conflate movement ready with native stopped queue or assume uniform-lane share alone causes it. '
          'Review Claude/source projections then use existing150s head/route records to separate SC6 through arrivals, ready transition, actual service and remaining stock. '
          'No repeated share/rate/ETA tuning or unconstrained free-right bonus. Preserve340 and earlier model as diagnostics. '
          'RM-vector delta remains-1.299 versus native-1.094; city large loss remains wrong. '
          'Preserve FW5/U10,450s,terminalOFF,Omega701,current route/lane,conservation,receiving. '
          'Full production integration, feasible selection and optimizer/runtime validation remain outstanding. No new native/full optimization/push for this diagnostic stage.')
    record=dict(status='bounded_candidate_rejected',completed_utc=stamp,goal_complete=False,production_adopted=False,
        new_forecasts=4,skipped_forecasts=2,new_native=0,ad=0,optimizer=0,fits=0,push=False,
        deltas=data['deltas'],native_delta={k:prior['contrasts'][k]['native'] for k in data['deltas']},
        queue_definition_diagnostic=proof,next_step=step,source_pins={str(p):sha(p) for p in (*HERE.glob('*.py'),HERE/'assessment.json',HERE/'README.md',HERE/'plan.json',HERE/'forecast2400/summary.json',A/'gain_account341/assessment.json')})
    (HERE/'completion.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for p in (A/'plan.json',A.parent/'plan.json'):
        plan=read(p);assert plan['current_stage']=='gain_account341_SC6_shared_lane_prehead_mismatch_identified'
        plan.update(current_stage='sc6_shared342_rejected_ready_stock_is_not_local_blocking_queue',current_workers=[],
            latest_stage=str(HERE/'README.md'),next_step=step,goal_complete=False,updated_utc=stamp,
            latest_goal_turn=dict(classification='progress',previous_goal_turn='progress341_gain_account_and_SC6_evidence',
                evidence='One physical-signal/shared-lane candidate tested4times; disabled response exact; real receive/conservation/caps pass but city sign worsens, local ready-stock mismatch identified. No repeat exploration/adoption.'))
        plan['sc6_shared342']={k:record[k] for k in ('status','completed_utc','new_forecasts','deltas','goal_complete','production_adopted')}
        p.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for p,link in ((A/'README.md','sc6_shared342/README.md'),(A.parent/'README.md','aggregate270/sc6_shared342/README.md')):
        text=p.read_text(encoding='utf8')
        intro=('# 최신342: 공유차로 우회전 후보 기각, 준비재고와 분기 차단 구분\n\n'
               'Claude 공유차로 근거를 확인해 신호 직접 제한과 부분 막힘을 분리했지만,4회 예측에서 도시 손익 방향은 개선되지 않았다. '
               '기본 비활성 전체response·보존·실제 수용·동일cap 검사는 통과했다. '
               '2700초 모델 직진 준비10~16대와 native 해당 도로 직진2대의 공간/정의 차이를 확인했다. '
               f'추가 비율 탐색 없이 도착·준비 전환·방출을 나누는 것이 다음 작업이다. [근거]({link}). '
               '운영 미채택·전체 목표 미완료; 새 native/최적화/fit/push0. 아래는 이전 기록이다.\n\n')
        p.write_text(intro+text,encoding='utf8')
    print('SC6_SHARED342_REJECTED_PROGRESS_RECORDED goal_complete=false')

if __name__=='__main__':main()
