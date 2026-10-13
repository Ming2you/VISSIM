"""Summarize the four completed fixed-command forecasts; no new predictions."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
read = lambda path: json.loads(path.read_bytes())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')


def main():
    result_path = HERE/'clock_comparison.json'
    assert not result_path.exists(), 'Reuse the completed comparison'
    results = {}
    for dt, name in ((1, 'pair2400_dt1_verified'), (10, 'pair2400_dt10')):
        assert read(HERE/name/'completion.json')['status'] == 'complete'
        item = read(HERE/name/'clock_response.json')
        for path, digest in item['source_pins'].items():
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
        hold, release = item['rows']
        assert hold['ramp_greens'] == [2.,2.,2.] and release['ramp_greens'] == [4.,6.,8.]
        for row in item['rows']:
            assert row['model_feasible'] and row['shared_constraints']['feasible']
            assert row['max_resource_excess'] < 1e-7
            assert row['transport_update_count'] == 450//dt
        times = [row['seconds'] for row in item['rows']]
        if dt == 10:
            events = [json.loads(line) for line in (HERE/'forecast2400_dt10/unused.joint.progress.jsonl').read_text().splitlines()]
            times[0] = next(row['seconds'] for row in events if row['stage']=='sdmpc_surrogate_batch_done')
        results[str(dt)] = dict(
            omega_ttt_veh_h=[row['omega_ttt_veh_h'] for row in item['rows']],
            release_minus_hold_ttt_veh_h=release['omega_ttt_veh_h']-hold['omega_ttt_veh_h'],
            merge10681_veh=[row['merge']['RM_C10681'] for row in item['rows']],
            release_minus_hold_merge10681_veh=release['merge']['RM_C10681']-hold['merge']['RM_C10681'],
            wout_stock_150_300_450=[row['wout_stock'] for row in item['rows']],
            release_minus_hold_wout450=release['wout_stock'][-1]-hold['wout_stock'][-1],
            release_minus_hold_owner_costs={key:release['costs'][key]-value for key,value in hold['costs'].items()},
            scalar_query_seconds=times, macro_updates_per_prediction=450//dt,
            all_model_and_shared_constraints_pass=True,
            max_resource_excess_veh=max(row['max_resource_excess'] for row in item['rows']))
    fine, coarse = results['1'], results['10']
    directions = {key: (fine[key]>0)==(coarse[key]>0) for key in (
        'release_minus_hold_ttt_veh_h', 'release_minus_hold_merge10681_veh', 'release_minus_hold_wout450')}
    assert all(directions.values())
    summary = dict(status='one_state_clock_direction_and_feasibility_passed',
        start_sec=2400, end_sec=2850, initial_wout_veh=55., results=results,
        same_control_direction=directions, scalar_predictions=4, optimizer_calls=0, native_runs=0,
        full_decision_600sec_qualified=False, production_default_enabled=False,
        limits=[
            'Only68/connectors/local lateral transport is replaced by10s fixed-size aggregate bins. Other urban mechanisms, ramp receiving and mainline retain fine steps.',
            'Same seed29 window state, not an independent-state/seed or native RM/VSL gain validation.',
            'RM is compared in the existing continuous-signal/cycle-mean-meter predictor. Three command blocks pass writer bounds, but were not applied to VISSIM.',
            'Macro FIFO, one average speed per stage and rounded ETA approximate detailed spatial queues. Neither actual stopped count nor exact trajectory equivalence is claimed.',
            'Four scalar timings under competing native workload do not establish full-optimizer speedup. Reused-file read time is not counted as prediction time.',
            'First1s diagnostic attempt stopped before any forecast because96from an earlier saved state was incorrectly hardcoded; current native-window W_out is55. Only the diagnostic was corrected; old failure retained.',
            'Full AD, autonomous SDMPC selection, held-out response and meaningful VSL gain validation remain.'
        ])
    save(result_path, summary)
    plan = read(HERE/'plan.json')
    plan['status'] = 'coarse_bridge_four_scalar_forecasts_passed_full_ad_and_selection_pending'
    plan['completed'].update(component_tests=115, parameter_verifier='PASS',
        canonical_prediction_connected=True, full_sdmpc_connected=False,
        new_full_forecasts=4, new_native_runs=0, clock_response_comparison='clock_comparison.json',
        current_native_window_initial_wout_veh=55.)
    plan['representation']['clock'] = 'Only68/connectors/local lateral transport10s; actual accepted transfers, other urban/ramp mechanisms, mainline and Omega ledger keep existing1s clock. Control150s, horizon450s.'
    plan['current_limits'] = summary['limits']
    plan['clock_candidate']['ttt'] = 'Existing fine-step single-owner Omega ledger retained with actual accepted flows; no duplicate aggregate residence cost'
    plan['clock_candidate']['production_adopted'] = False
    plan['next'] = [
        'Compare the aggregate response at saved3300 against the retained native controls/stock observations with canonical current initialization; no calibration grid or new native run.',
        'Check one full derivative path only after the large response direction and physical checks pass; scalar success is not AD or whole SDMPC qualification.',
        'Extend aggregate interval treatment only where full-profile evidence supports it; avoid replacing the short-cell mainline step by10s blindly.',
        'Measure one complete SDMPC decision against600s once the reduced predictor is qualified. Do not claim10x full speedup from45 macro updates.'
    ]
    source_files = ['reservoir.py','compare_clock.py','report_clock.py','config_dt1.json','config_dt10.json']
    plan['coupled_bridge_source_sha256'] = {p:hashlib.sha256((HERE/p).read_bytes()).hexdigest() for p in source_files}
    plan['coupled_bridge_source_sha256'].update({str(Path(p).relative_to(ROOT)):h for p,h in item['source_pins'].items() if Path(p).is_relative_to(ROOT/'evaluation')})
    save(HERE/'plan.json', plan)
    report = '''# 10초 집계 갱신 연결 검증

68번 도로·진입 커넥터·국소 차로 변경을 고정 크기의 차로/회전 재고로 바꾸고, 10초마다 이동을 갱신했다. 실제 램프 수용과 본선 합류, 다른 도시부 계산, Ω 비용 장부는 기존 짧은 시간 간격을 유지한다. 설정 `urban.known_wout_aggregate_step_sec`를 명시해야 작동하며 기본 실행·동결 native 큐는 바꾸지 않았다.

seed29 window 런의2400초 저장 상태에서450초 예측4회를 완료했다. 현재 초기 W_out은55대다. 앞서 투영했던 다른2400초 상태의96대와 구분한다. 동일 초기 상태·같은 신호/VSL/NP/NUF에서10681 RM만 유지[2,2,2]와 완화[4,6,8]초를 비교했다. 초기화·명령·소스 일치, 차량 보존·유한 수용·공유 제약·3블록 writer 검사PASS. 성분/회귀115시험 및 설정 검사PASS.

| 집계 갱신 | 유지 ΩTTT | 완화 ΩTTT | 완화−유지 | 합류량 변화 |450초 말 W_out 변화 |
|---|---:|---:|---:|---:|---:|
'''
    for dt, row in results.items():
        report += f"|{dt}초|{row['omega_ttt_veh_h'][0]:.3f}|{row['omega_ttt_veh_h'][1]:.3f}|{row['release_minus_hold_ttt_veh_h']:+.3f}|{row['release_minus_hold_merge10681_veh']:+.2f}|{row['release_minus_hold_wout450']:+.2f}|\n"
    report += '''
TTT 단위는대·시간, 재고·합류량은대다. 두 갱신 간격에서 RM 반응의 방향이 유지됐다. 이것은 같은 모델의 갱신 간격 비교이며, native 제어 이득을 새로 재현했다는 뜻이 아니다. 특히 VSL 손익 검증은 별도로 남아 있다.

450초 중 해당 이동 갱신은450→45회다. scalar 예측 시간은1초 모형39.14/35.46초,10초 모형36.08/32.44초였다. 다른 native 계산이 동시에 실행 중이었으므로 확정 가속률이나 전체 선택600초 달성으로 해석하지 않는다. 본선 최단76.03m 셀에10초를 그대로 적용하지 않았다.

현재 평균 단계 속도·차로별 부분 FIFO·다음 경계 ETA 반올림을 쓰는 집계 근사다. 상세 차량순서/횡방향 gap을 재현하지 않는다. 첫1초 비교 스크립트의96대 고정 검사 오류는 예측 시작 전에 확인했고, 현재 관측을 투영한 소유 재고와 대조하도록 수정했다. 실패 폴더를 보존했다. 생산 물리식은 그 오류 때문에 수정하지 않았다.

다음은 미사용3300초 응답, 역미분, 전체SDMPC 선택/계산시간 검증이다. 실행되지 않은 단계나600초 목표를 완료로 처리하지 않는다. 원자료: `clock_comparison.json`, 각 `clock_response.json`, `completion.json`, `protocol.json`.
'''
    (HERE/'README.md').write_text(report, encoding='utf8')
    parent = read(HERE.parent/'plan.json')
    parent['status'] = 'aggregate_dynamics_replacement_in_progress'
    parent['aggregate270_latest'] = dict(report='aggregate270/README.md',
        result='aggregate270/clock_comparison.json', canonical_scalar_forecasts=4,
        current_initial_wout_veh=55, direction_preserved=True, full_selection_qualified=False,
        native_changed=False, next='held-out3300 response, derivative and full decision timing')
    save(HERE.parent/'plan.json', parent)
    with (HERE.parent/'README.md').open('a', encoding='utf8') as file:
        file.write('\n\n### 10초 집계 모형 실제 연결 검증 완료 (부분 연결,2026-10-09)\n\n'
            '위의 미연결 시제품 상태는 갱신됐다.68/connector/lateral 이동의 opt-in 생산 연결 후 실제 정본 scalar450초4회와115시험을 통과했다. 다른 도시부·램프 수용·본선·Ω 장부는1초를 유지한다. 현재 window2400 W_out55대이며 예전 투영96대와 다르다. RM[2,2,2]→[4,6,8]시1초/10초의 예측 ΔΩTTT는−0.807/−0.662vehh,실제 허용 합류량 변화는+68.90/+68.92대다. 방향이 같지만 native 이득 검증은 아니다. 해당 이동 갱신450→45회;전체AD/선택600초 목표는 미완료다. 동결 native·기본 설정은 그대로다. 자세한 근거와 진단 실패 보존은 aggregate270/README.md 및clock_comparison.json.\n')
    print(json.dumps({k:summary[k] for k in ('status','same_control_direction','scalar_predictions','full_decision_600sec_qualified')}, indent=2))


if __name__ == '__main__':
    main()
