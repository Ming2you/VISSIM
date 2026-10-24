"""Persist the finite diagnostic result without changing production or runtime."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re

HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_bytes())


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def main():
    assert not (HERE/'final_checks.json').exists()
    plan=read(HERE/'plan.json')
    for path,digest in plan['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    report=read(HERE/'assessment.json')
    assert report['forecasts_completed']==3 and not report['calibration_control_gate_passed']
    assert report['fresh3300']['local_improved']
    completions={str(at):read(HERE/f'completion{at}.json') for at in (2400,3300)}
    assert all(c['status']=='complete' and c['exit_code']==0 for c in completions.values())
    old=read(H/'spatial_receiving/forecast2400/network.json')
    new=read(HERE/'forecast2400/network.json')
    assert set(old)==set(new)
    changed=[key for key in old if old[key]!=new[key]]
    assert changed==['movement_capacity_by_movement_veh_h'],changed
    field=changed[0]
    movements=[key for key in old[field] if old[field][key]!=new[field][key]]
    assert movements==['SC101_S_SC1_to_N_SC2005']
    before_state=read(H/'spatial_receiving/forecast2400/state.json')
    after_state=read(HERE/'forecast2400/state.json')
    opaque_paths=[]
    def normalize(value,path=''):
        if isinstance(value,dict):
            return {key:normalize(item,path+'/'+key) for key,item in value.items()}
        if isinstance(value,list):
            return [normalize(item,path+'/'+str(index)) for index,item in enumerate(value)]
        if isinstance(value,str) and re.fullmatch(r'<evaluation\.controllers\.[A-Za-z_.]+ object at 0x[0-9A-Fa-f]+>',value):
            opaque_paths.append(path)
            return re.sub(r' at 0x[0-9A-Fa-f]+>','>',value)
        return value
    assert normalize(before_state)==normalize(after_state)
    assert len(opaque_paths)==14 and len(set(opaque_paths))==7
    save(HERE/'final_checks.json',dict(status='passed',source_pins=len(plan['source_pins']),
        serialized_initial_fields_equal=True,opaque_runtime_objects_not_deep_compared=sorted(set(opaque_paths)),
        network_changed_fields=changed,changed_movements=movements,
        completions=completions,physical_checks=report['physical'],
        previous_service_unit_tests_reused=7,new_unit_tests=0,new_parameter_fits=0,
        fixed_predictions=3,full_ad=0,full_sdmpc=0,new_native=0,
        failures_preserved=['preparation_failure_preserved.json',
            'First final state equality check failed only on7object address reprs; same classes and all serialized fields pass, opaque contents not certified.',
            'upstream_cost_split_first.json (duplicate66gate listing corrected;delta unchanged)'],
        production_changed=False,live_queue_modified=False))
    plan.update(status='complete_local_service_improvement_joint_gain_unqualified',
        predictions_completed=3,conditional3300_executed=True,assessment='assessment.json',
        next='No further head-rate search. Audit SC6 supply/transport timing against current queues and accepted upstream flow using existing Claude findings and closed ledgers. Do not refit10681 to absorb unrelated joint-city error.',
        calibration_control_gate_passed=False,runtime_pair_launched=False)
    save(HERE/'plan.json',plan)
    root=read(H/'plan.json')
    root['sc101_recombined']=dict(status=plan['status'],plan='sc101_recombined/plan.json',
        upstream_cost_split='sc101_recombined/upstream_cost_split.json',assessment='sc101_recombined/assessment.json',
        fixed_predictions=3,new_fits=0,production_changed=False,native_runs=0)
    root['next']=plan['next']
    root['previous_goal_turn']=dict(time_utc=datetime.now(timezone.utc).isoformat(),classification='progress',
        completed=[
            'Closed-ledger decomposition:52/58benefit is underpredicted and66error small; residual is not solely10681 response.',
            'One existing SC101 service ceiling combined with corrected SC1 supply; paired450x2 plus3300fresh150 completed, no new fits.',
            'Six-bin head absolute error49.483->37.820;3300head57.741->58.375/native62; same serialized initial fields, one network capacity change, conservation and paired caps pass.',
            'WholeOmega delta-5.681->-4.933/native+4.193 remains unqualified; stop this candidate without grid/fullAD/fullselection/native.'
        ],next=plan['next'])
    root['runtime_priority']['calibration_then_wall']=True
    root['runtime_priority']['full_wall_comparison_launched']=False
    save(H/'plan.json',root)
    entry='''\n\n2026-10-09 SC101 보완 재조합 완료: `sc101_recombined/README.md`.
SC1 공급 수정 후에도 남은 SC101 직진 상한에 과거 검증값 한 개를 재사용했다.
고정450초2회+3300초 상태의150초1회, 새 계수 추정0회/전체SDMPC0회/native0회.
방출량 오차는 줄었으나 전체 Ω 손익 방향은 미통과다. 같은 상한 추가 탐색 없이
SC6 공급·현재 이동 차량·고정신호 구간의 연결을 기존 자료로 진단한다.
보정/제어 판단 검증 후 전체SDMPC wall 비교 순서를 유지하며 실행 중인 큐는 변경하지 않았다.
'''
    with (H/'README.md').open('a',encoding='utf8') as f:f.write(entry)
    print(json.dumps(dict(status=plan['status'],changed=movements,completions=completions),ensure_ascii=False))


if __name__=='__main__':main()
