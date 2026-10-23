"""Register completed offline evidence without changing production or old reports."""
import datetime
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
HERE=OUT.parent
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def main():
    assert not (OUT/'decision.json').exists(),'Preserve completed registration'
    evidence=[OUT/n for n in ('summary.json','approach_flux.json','approach_terms_summary.json','approach_lane_evidence.json','independent_approach.json')]
    documents=[read(p) for p in evidence]
    for doc in documents:
        assert doc['new_native']==0 and doc['new_forecasts']==0 and doc['new_fzp_scans']==0 and doc['production_edits']==0
        for path,digest in doc['source_pins'].items():assert sha(Path(path))==digest,path
    terms=documents[2]
    assert sum(x['terms'] for x in terms['cases'].values())==3115
    assert terms['max_recorded_speed_error']<2e-5 and terms['max_stock_error']<1e-7
    assert len(documents[3]['rows'])==240 and len(documents[4]['rows'])==6
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    record=dict(status='approach_response_localized_no_correction_adopted',updated_utc=now,app_goal_status='active',goal_complete=False,
                previous_goal_turn='progress: new saved native boundary evidence located the response mismatch',
                current_goal_turn='progress: exact cached speed-term decomposition, native diverge/lane evidence, and existing independent-pair cut responses changed correction criteria',
                new_native=0,new_forecasts=0,new_optimizer_runs=0,new_fzp_scans=0,new_fits=0,production_edits=0,
                candidate_adopted=False,remaining_native_budget=0,automation_status='PAUSED',
                evidence={str(p):sha(p) for p in [*evidence,OUT/'README.md']},
                correction_not_yet_verified=['No justified production correction yet','Independent response validation of a correction pending','NP/NUF, actuator, AD and walltime validation of a correction pending'],
                next='Audit aggregate representation of diverge lane imbalance and within-approach congestion location against prior183/195/212/213/247 before proposing one nonduplicate conservative closure. No blanket lane-drop removal, VSL reward, duplicate center-distance/phase/numerics experiments or new native.')
    for name in ('plan.json','summary.json'):
        path=HERE/name;backup=HERE/(path.stem+'_before_offline_followup_20261019.json')
        assert not backup.exists()
        backup.write_bytes(path.read_bytes())
        doc=read(path)
        doc['status']='offline_approach_response_diagnosis_active'
        doc['app_goal_status']='active'
        doc['updated_utc']=now
        doc['offline_followup_20261019']=record
        if name=='plan.json':
            doc['app_goal_registration']='get_goal during2026-10-19 continuation confirms ACTIVE; prior BLOCKED records are historical; objective incomplete.'
            doc['next']=record['next']
        save(path,doc)
    save(OUT/'decision.json',record)
    with (HERE/'README.md').open('a',encoding='utf8') as f:
        f.write('\n\n## 2026-10-19 오프라인 후속 — 목표 ACTIVE·미완료\n\n')
        f.write('실제 앱 목표는 ACTIVE로 확인했다. 앞선BLOCKED 문구는 역사이며 유한native 자동확인은PAUSED를 유지한다. 새 저장 관측에서 접근부14–18 통과량은 두 구역90 실제+31대/모델−28.868대, 재고는실제−30대/모델+26.052대로 확인했다. 속도 갱신3,115개를 정확히 복원했고 실제 분기 연결과240개 차로 단면, 기존seed67/71의6개horizon 비교를 추가했다. 모든 새native/예측/최적화/FZP/생산 변경은0이다. 일괄 방출 확대나차로 감소항 제거는채택하지 않았다. 상세와남은검증은[outflow followup](outflow_followup_20261019/README.md), 정본 결정은outflow_followup_20261019/decision.json이다. 보정 완료가 아니다.\n')
    print(json.dumps({'status':record['status'],'evidence_files':len(record['evidence']),'goal_complete':False}))


if __name__=='__main__':main()
