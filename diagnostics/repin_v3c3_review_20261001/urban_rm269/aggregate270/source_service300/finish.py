"""Validate completed300 evidence and update only working diagnostic plans."""
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT))
from diagnostics.validate_native_signal_record import read_ldp_frames


def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (HERE/'completion.json').exists()
    reports={n:read(HERE/n) for n in ('assessment.json','source_audit.json','routing_audit.json')}
    pins={}
    for name,report in reports.items():
        assert report['status'].startswith('complete') and report['goal_complete'] is False
        for p,h in report['source_pins'].items():assert sha(p)==h,p
        pins.update(report['source_pins']);pins[str(HERE/name)]=sha(HERE/name)
    cache=read('E:/VISSIM_analysis/20261010_sc15_source300/completion.json')
    green={}
    for arm,rows in reports['source_audit.json']['arms'].items():
        fzp=Path(cache['arms'][arm]['source']);stem=fzp.stem.removesuffix('_001')
        ldp=read_ldp_frames({15:fzp.parent/(stem+'_15_001.ldp')},{15:list(range(1,9))},2400,2850)
        for p,d in ldp['pins'].items():assert sha(p)==d['sha256'];pins[p]=d['sha256']
        green[arm]={}
        for dec,row in rows.items():
            sg='5' if dec=='1099' else '1';blocks=[]
            for b in row['blocks']:
                st=b['start_sec']
                events=[e for e in row['events'] if e['lower_sec']>=st and e['upper_sec']<=st+150]
                full=[e['veh'] for e in events if all(ldp['frames'][s][f'15:{sg}']=='GREEN'
                    for s in range(math.floor(e['lower_sec']),math.ceil(e['upper_sec'])))]
                assert len(full)>b['model_all_branch_departures']
                assert b['model_green_sec']==b['native_green_sec']==35
                blocks.append(dict(start_sec=st,fully_green_crossing_lower=len(full),vehicle_ids=full,
                    model_full_green_capacity_veh=b['model_all_branch_departures']))
            green[arm][dec]=blocks
    (HERE/'green_witness_audit.json').write_text(json.dumps(dict(status='complete',arms=green,
        interpretation='Even entirely GREEN5s crossing witnesses exceed the model full-GREEN source capacity. Not a fitted saturation rate.'),indent=2)+'\n',encoding='utf8')
    for p in (HERE/'green_witness_audit.json',HERE/'README.md',Path(__file__),HERE/'extract_sc15.py'):
        pins[str(p)]=sha(p)
    record=dict(status='complete_source_service_and_turn_scope_diagnostic_not_adopted',goal_complete=False,
        previous_goal_turn_classification='no_progress_configuration_restatement',
        current_goal_turn_classification='progress_new_closed_source_and_routing_evidence',
        new_evidence='SC15 actual fully-green source lower bounds exceed old model cap; side entries bypass1014 and enter distinct lanes;10528 bypass and head-to-left overlaps documented.',
        budget=dict(conditional_local_replays=8,closed_fzp_passes=2,new_full_forecasts=0,new_ad=0,
            new_optimizations=0,new_native=0,new_fits=0,production_changes=0,pushes=0),source_pins=pins,
        preserved=['FW/ramp5 urban10 candidate','450s horizon terminalOFF','demand/Omega701','current native queue/frozen tree'],
        next_step='Verify past-only current-network SC15 queued discharge and source/lane turning scope before one bounded candidate; do not fit2400–2850 validation or repeat SC101-cap-only exploration.',
        updated_utc=datetime.now(timezone.utc).isoformat())
    (HERE/'completion.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    relative=str((HERE/'README.md').relative_to(ROOT)).replace('\\','/')
    for parent in (A,A.parent):
        p=parent/'plan.json';plan=read(p)
        plan.update(status='fw5_urban10_runtime_verified_sc15_source_and_turn_scope_identified_city_gain_unqualified',
            current_stage='source_service300_complete_diagnostic_not_adopted',latest_stage=relative,current_workers=[],
            goal_complete=False,next_step=record['next_step'],last_goal_turn=record['current_goal_turn_classification'],
            updated_utc=record['updated_utc'],source_service300=dict(status=record['status'],
                completion=str((HERE/'completion.json').relative_to(ROOT)).replace('\\','/'),
                completion_sha256=sha(HERE/'completion.json'),budget=record['budget']))
        p.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        path=parent/'README.md';text=path.read_text(encoding='utf8')
        header='# 최신: SC15 공급 상한·유입별 경로 감사(300)\n\n완료된 자료에서 SC15 두 원천의 녹색 통과 하한14–17대/150초가 모델 상한12–13대를 넘음을 확인했다. 두 원천은 RD1014 뒤로 서로 다른 차로에 합류하지만 모델은 공통 SC101 회전비율로 합친다. 10528 신호 전 우회전과 head 이후 좌회전 관측을 분리했다. 과거 자료에 근거한 원천별 서비스·경로 확인이 다음 단계이며, 검증 미래에 맞춘 계수나 전체 런은 추가하지 않았다. 전체 도시 손익·목표는 미완료. 상세: '+relative+'\n\n---\n\n'
        path.write_text(header+text,encoding='utf8')
    print('COMPLETE300',len(pins),'verified pins; goal remains active; no forecast/native/production changes')


if __name__=='__main__':main()
