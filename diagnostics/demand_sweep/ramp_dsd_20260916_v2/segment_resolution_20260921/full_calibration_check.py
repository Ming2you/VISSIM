"""Post-fit checks only: never select coefficients using controlled traffic."""
import json
import full_calibration as f
from prepare import save,table
c=f.c;B=f.B;O=f.O;K=f.K;ROOT=f.ROOT


def packing_audit(identification):
    path=K/'current_mainline_route_v1/result.json'
    lengths=[v['length_m'] for v in c.load(path)['current_vehicles'] if v['length_m']>0]
    mean=sum(lengths)/len(lengths);zero_gap=1000/mean
    return dict(source=str(path.relative_to(ROOT)),sha256=c.sha(path),vehicles=len(lengths),mean_length_m=mean,
        zero_gap_current_mix_veh_km_lane=zero_gap,
        cases_exceeding_current_mix_zero_gap=[k for k,v in identification.items() if v['values']['rho_jam']>zero_gap],
        note='Current observed vehicle mix, not a universal bound for every future lane mix. A value above this needs independent physical support and is not qualified for adoption.')


def jacobian_audit(role,selected,sensitivity):
    import numpy as np
    keys=selected['scope'];history=c.load(O/(role+'_history.json'))
    coordinates=np.array([[(r['spec']['calibration_values'][k]-f.BOUNDS[k][0])/(f.BOUNDS[k][1]-f.BOUNDS[k][0]) for k in keys] for r in history])
    def vector(x):
        distances=np.max(np.abs(coordinates-x),axis=1);i=int(np.argmin(distances))
        assert distances[i]<1e-10
        row=history[i];assert row['exit_code']==0 and row['numerics']['passed']
        return np.load(O/(row['name']+'_residual.npy'))
    x=np.array(sensitivity['x']);base=vector(x);columns=[]
    for j,row in enumerate(sensitivity['sensitivity']):
        assert row['parameter']==keys[j]
        z=x.copy();z[j]+=row['normalized_step']
        columns.append((vector(z)-base)/row['normalized_step'])
    singular=np.linalg.svd(np.stack(columns,axis=1),compute_uv=False)
    return dict(singular_values=singular.tolist(),relative_rank_1e_3=int(sum(singular>singular[0]*1e-3)),
        note='Local finite-difference sensitivity, not statistical or global identifiability.')


def report(receipt):
    labels=list(receipt['identification']);metrics=receipt['metrics'];gains=receipt['gains']
    late=[r for r in metrics if r['scope']=='fit_cells' and r['phase']=='late']
    baseline=next(r for r in late if r['case']=='disabled');best=min((r for r in late if r['case']!='disabled'),key=lambda r:r['objective'])
    reduction=100*(1-best['objective']/baseline['objective'])
    lines=['# 전체 계수 공동 재보정 — 2026-09-21',
        '', '## 범위와 결론', '',
        'Hadiuzzaman 고정 파속 수용식과 Wang–Niu 혼잡 파속 수용식 각각에 대해, 기존 FD 상한 속도식과 명령속도 이완식을 재보정했다. '
        '기하·수요·경로·RM/VSL 실행 명령·대기 비용은 고정했다. 동측 물리 모델의 독립 연속계수는 Hadi 17개, Wang 16개다. '
        'Wang의 파속은 용량·밀도·자유속도로 계산하므로 별도의 독립 변수가 아니다.',
        '', '계수 탐색에 모두 포함했다는 것과 모든 계수가 실측에서 식별됐다는 것은 다르다. '
        '이는 한 초기 상태의 유한 범위 국소 최적화이며, 독립 표본 검증이나 전역 최적해 인증이 아니다. '
        '기본 설정은 교체하지 않았다.',
        '',f"뒤쪽 검증 구간의 복합 오차가 가장 낮은 {best['case']}는 {baseline['objective']:.4f}→{best['objective']:.4f} "
        f"({reduction:.1f}% 감소)다. 이것은 사후 비교 결과이며 전체 모델 선정이나 제어 성능 개선율이 아니다. "
        'RM/VSL 이득의 크기와 부호는 아래 표로 별도 판단한다.',
        '',f"완료된 오프라인 450초 예측: {receipt['forecast_count']}회. 새 VISSIM 실행: 0회. 기존 seed 23 실측을 사용했다. "
        '미분용 계수 교란·반복 NC·검증 예측도 이 횟수에 포함되며 독립 교통 실험 수가 아니다.',
        '', '## 보정과 검증 구분', '',
        '- 초기 관측: 2400초. 보정: NC 2400–2700초의 차로군 속도·차량 수·경계 통과량.',
        '- 목적값: (속도 RMSE/20)² + (차로군 차량 수 RMSE/5)² + (통과유량 RMSE/500)². 이득 부호를 맞추는 보상항을 추가하지 않았다.',
        '- 계수 고정 후: NC 2700–2850초, 그리고 NC/RM/VSL/동시 제어의 450초 비교.',
        '- 같은 초기 상태와 이전에도 살펴본 개발 자료다. 새 초기 상태·새 seed 검증은 이번에 수행하지 않았다.',
        '- 정본 생산 설정의 5초 적분·기록은 유지했다. 짧은 세그먼트 진단은 기존과 같은 1초 적분이다.',
        '- 제어 비용 범위는 동측 본선+4개 on/off connector다. 전체 Ω TTT나 폐루프 MPC 성능으로 해석하지 않는다.',
        '', '## 상태 예측 오차', '',
        '| 모델 | 구간 | 복합 오차 | 속도 RMSE km/h | 차로군 N RMSE 대 | 경계 q RMSE 대/h |',
        '|---|---|---:|---:|---:|---:|']
    for r in metrics:
        if r['scope']=='fit_cells':lines.append(f"| {r['case']} | {r['phase']} | {r['objective']:.4f} | {r['speed_rmse_kmh']:.3f} | {r['group_n_rmse_veh']:.3f} | {r['boundary_q_rmse_vph']:.2f} |")
    lines+=['','다른 동측 세그먼트에 대한 오차도 state_metrics.csv의 east_nonterminal에 기록했다. '
        '실측 종단 통과가 없는 마지막 셀의 0 채움 유량은 평가에서 제외했다.',
        '', '## 제어 이득: ΔTTT [대·시간], 음수가 개선', '',
        '| 모델 | RM | VSL | RM+VSL |', '|---|---:|---:|---:|',
        '| VISSIM 실측 | -0.55333 | -0.98194 | -0.51500 |']
    for label in ['disabled']+labels:
        row={r['arm']:r for r in gains if r['case']==label}
        lines.append('| '+label+' | '+' | '.join(f"{row[a]['predicted']:+.5f}" for a in f.ARMS[1:])+' |')
    wr=next((r for r in gains if r['case']=='wang_fd_cap_r2' and r['arm']=='rm_ramp'),None)
    if wr:
        real=c.load(B.parent/'response_chain_20260921/qualification.json')['gains']['rm_ramp']['actual']
        lines+=['',f"Wang+FD의 RM 비용 분해: 본선 {wr['mainline']:+.5f} (실측 {real['mainline']:+.5f}), "
            f"on-ramp {wr['on']:+.5f} (실측 {real['on']:+.5f}), off-ramp {wr['off']:+.5f} (실측 {real['off']:+.5f}). "
            f"10490 합류 변화는 {wr['delta_merge10490']:+.3f}대다. 미터가 물리적으로 아무 효과도 없는 예측은 아니다. "
            '램프 대기 비용보다 본선 이득의 누락이 큰지 이 분해로 판단해야 한다.']
    lines+=['', 'gain_check.csv에는 본선·on-ramp 대기·off-ramp 대기 비용과 실제 합류·방출량 차이를 분리했다. '
        '차량 보존을 통과하거나 상태 RMSE가 줄었다는 이유로 제어 이득 보정 성공으로 판정하지 않는다.',
        '', '## 계수와 종료 조건', '',
        '| 모델 | 최적화 종료 | 국소 민감도 rank / 계수 수 | 이번 유한차분 검사에서 반응 0인 계수 |',
        '|---|---|---:|---|']
    for label,r in receipt['identification'].items():
        lines.append(f"| {label} | {r['optimizer']['message']} | {r['jacobian']['relative_rank_1e_3']} / {len(r['last_sensitivity'])} | {', '.join(r['all_probes_inactive']) or '없음'} |")
    lines+=['', 'rank는 정규화된 국소 미분 행렬의 최대 특잇값 대비 10⁻³ 기준이다. 통계적 식별성의 증명이 아니다. '
        '반응 0은 이번 자료와 탐색 이웃에 대한 결과이며, 전체 허용 영역이나 다른 혼잡 상태에서 항이 항상 비활성이라는 뜻이 아니다. '
        '선택값은 미분용 교란점을 포함한 유효 NC 평가점 중 최소 오차점이다. 종료 코드는 최적화 경로의 종료 사유이며 선택점의 최적성을 인증하지 않는다. '
        '종료 코드 0은 평가 예산 소진이며 수렴으로 표기하지 않는다. 계수 경계·미분폭은 protocol.json, '
        '모든 실효값과 분기 사용 횟수는 각 후보의 effective_config.json 및 anticipation_none.json에 있다.',
        '', '| 계수 | '+' | '.join(labels)+' |', '|---|'+'---:|'*len(labels)]
    for key in f.BOUNDS:
        lines.append('| '+key+' | '+' | '.join('파생값' if key=='wave' and label.startswith('wang') else f"{receipt['identification'][label]['values'][key]:.6g}" for label in labels)+' |')
    lines+=['', 'Wang 파속의 실제 파생값은 각 후보 hadiuzzaman.cells[].wave_kmh에 저장돼 있다. '
        'wave라는 공통 입력의 사용하지 않는 초기값을 Wang의 보정 결과로 읽지 않는다. '
        'theta는 모형 안에서 탐색한 계수이며, 실측 방출량에서 capacity drop을 독립적으로 확인했다는 뜻은 아니다.',
        '',f"jam density 물리성 점검: 관측 {receipt['packing']['vehicles']}대의 평균 길이는 {receipt['packing']['mean_length_m']:.3f}m, "
        f"이 구성의 무간격 밀도는 약 {receipt['packing']['zero_gap_current_mix_veh_km_lane']:.1f}대/km/차로다. "
        f"이를 초과한 후보는 {', '.join(receipt['packing']['cases_exceeding_current_mix_zero_gap']) or '없음'}이다. "
        '모든 미래 차로의 보편 상한은 아니지만, 이 수치는 별도 물리적 근거 없이 생산 설정에 채택할 수 없다. '
        '수치 안정성 통과와 파라미터 물리성 검증은 별개다.',
        '', '## 검증과 재현', '',
        '- 관련 단위 테스트 45개 통과. 기본 기능 비활성의 4개 전체 예측 JSON은 기존과 정확히 일치.',
        f"- 검증 {len(receipt['numerics'])}개 예측의 보존·밀도·Courant·최대속도 검사 통과. 서측 {receipt['west_exact']}개 예측의 cells/flows 배열 정확히 일치.",
        '- 각 모델의 보정 NC와 4조건 재실행 NC 전체 예측이 정확히 일치. 모든 선언 계수를 실제 cfg/row에 대조.',
        '- verify_parameters.py로 실행에 쓴 기본 config PASS. 이 검사는 런타임 진단 보정값까지 검사하지 않으므로 별도의 실효값 대조를 수행했다.',
        '- 본선/램프 공동 수용 예산 위반 검사 통과. 원점 희망/진입/잔여 대기는 flows.csv에 별도 기록.',
        '- 종단 zero-gradient는 기존 진단의 경계 조건이다. 실측 종단 공급에 대한 독립 보정으로 해석하지 않는다.',
        '- core·adapter·parameters.json은 이 작업에서 변경하지 않았다. runner의 실효계수 연결·gzip 저장·공유 초기파일 읽기만 확장.',
        '- 현재 실행 함수는 full_calibration.py의 fit/resume/actions, 사후 검사는 full_calibration_check.py. '
        'SciPy 1.16.2는 tmp/calibration_dependencies에만 설치했다.',
        '', '## 다음 판단', '',
        '이번 범위에서 공동 계수 보정만으로 이득 예측이 완성되지는 않았다. '
        '네 모델 모두 RM 순이득 부호는 맞지만 실제 이득을 작게 예측하고, VSL은 모두 부호가 틀리다. '
        '따라서 상태 오차가 가장 작은 모델을 바로 MPC에 올리지 않는다.',
        '', '다음에는 기존 matched RM/VSL 기록의 실제 합류 변화, 본선 방출·회복 변화, 램프·도시 대기 증가를 '
        '함께 사용해 제어 응답을 식별하는 것이 타당하다. 보정에 사용할 명령/시간과 검증할 명령/시간을 먼저 분리하고, '
        '순이득에 맞춘 임의 보상 대신 각 물리 응답과 비용 항이 맞는지 검사한다. '
        '그 다음 새 초기 상태 또는 새 seed에서 확인해야 한다. 이번 결과만으로 METANET 전체의 표현 불가능성을 증명한 것은 아니다.',
        '', '세부 근거: validation.json, state_metrics.csv, gain_check.csv, flows.csv, *_selected.json, *_history.json, *_sensitivities.json. '
        '원시 예측은 후보별 .json.gz로 보존했다. 로컬 결과이며 아직 push하지 않았다.', '']
    (O/'README.md').write_text('\n'.join(lines),encoding='utf-8')


def main(labels):
    actual=c.load(B.parent/'response_chain_20260921/qualification.json')['gains']
    metrics=[];gains=[];checks=[];flows=[];audits={};identification={}
    roles=[('disabled','fc_disabled')]+[(x,'fc_'+x+'_actions') for x in labels]
    for role,name in roles:
        result=c.load(K/('segment_resolution_20260921_cal_'+name)/'result.json')
        role_flows={}
        for arm in f.ARMS:
            p=f.load_prediction(O/name/f'refined_guard1_{arm}.json')
            old=c.load(B/f'refined_guard1_{arm}.json')
            check=c.screen(p);assert check['passed'];checks.append(dict(case=role,arm=arm,**check))
            for key in ('cells','flows'):
                assert [r for r in p[key] if r['road']=='FW_W']==[r for r in old[key] if r['road']=='FW_W']
            if role=='disabled':assert p==old
            d=next(x for x in p['diagnostics']['roads'] if x['road']=='FW_E')
            if role!='disabled':
                a=d['hadiuzzaman_audit'];assert a['max_budget_violation_veh']<1e-7
                audits[role+':'+arm]=a
                if 'fd_cap' in role:assert a['desired_changed']==0
            if arm=='none':
                for phase,lo,hi in [('train',0,10),('late',10,15)]:
                    metrics.append(dict(case=role,phase=phase,scope='fit_cells',**c.score(p,lo,hi)))
                    # Native disappearance is not a measured terminal crossing;
                    # its zero-filled q label must not score the final cell.
                    metrics.append(dict(case=role,phase=phase,scope='east_nonterminal',**c.score(p,lo,hi,cells=list(range(30)))))
            else:
                delta=result['deltas'][arm]
                gains.append(dict(case=role,arm=arm,actual=actual[arm]['actual']['total'],predicted=delta['total'],
                    mainline=delta['mainline'],on=delta['on'],off=delta['off'],sign_correct=delta['total']<0))
            flow=dict(case=role,arm=arm,merge10490=sum(r['accepted_merge_veh'] for r in p['ramps'] if r['ramp']=='RM_C10490'),
                on10490_ttt=sum(r['connector_ttt_veh_h'] for r in p['ramps'] if r['ramp']=='RM_C10490'),
                origin_requested=d['requested_source_veh'],origin_admitted=d['accepted_source_veh'],
                origin_final_queue=d['final_origin_queue_veh'])
            for key in ('ramp_merges','off_departures','terminal_exits'):
                flow[key]=sum(r[key] for r in p['flows'] if r['road']=='FW_E')
            role_flows[arm]=flow;flows.append(flow)
        for arm in f.ARMS[1:]:
            row=next(r for r in gains if r['case']==role and r['arm']==arm)
            for key in ('merge10490','on10490_ttt','ramp_merges','off_departures','terminal_exits'):
                row['delta_'+key]=role_flows[arm][key]-role_flows['none'][key]
        if role!='disabled':
            selected=c.load(O/(role+'_selected.json'))
            assert f.load_prediction(O/selected['selected']['name']/'refined_guard1_none.json')==f.load_prediction(O/name/'refined_guard1_none.json')
            sens=c.load(O/(role+'_sensitivities.json'))
            identification[role]=dict(optimizer=selected['optimizer'],values=selected['selected']['spec']['calibration_values'],
                all_probes_inactive=[key for key in selected['scope'] if all(next(r['response_norm'] for r in s['sensitivity'] if r['parameter']==key)<1e-10 for s in sens)],
                last_sensitivity=sens[-1]['sensitivity'],jacobian=jacobian_audit(role,selected,sens[-1]),independent_identification=False)
    pin_count=0
    for path,pin in c.load(O/'before_sources.json').items():
        # Runner was intentionally extended; core/config/calibration baseline stay fixed.
        target=ROOT/path
        if target.name=='run.py':target=O/'run.py.before.txt'
        assert c.sha(target)==pin,path;pin_count+=1
    for manifest in ('protocol.json','continuation_protocol.json'):
        protocol=c.load(O/manifest)
        for path,pin in protocol.get('source_pins',protocol.get('sources',{})).items():
            target=ROOT/path
            assert any(p.exists() and c.sha(p)==pin for p in (target,O/(target.name+'.stage1.txt'))),path
            pin_count+=1
    for name,rows in [('state_metrics.csv',metrics),('gain_check.csv',gains),('flows.csv',flows),('numerics.csv',checks)]:table(O/name,rows)
    forecasts=sum(c.load(p)['forecasts'] for p in O.glob('*/refined_guard1_receipt.json'))
    receipt=dict(status='RECALIBRATED_NOT_QUALIFIED',production_adopted=False,new_native_runs=0,
        independent_validation=False,source_checks=pin_count,default_exact=4,west_exact=4*len(roles),
        forecast_count=forecasts,numerics=checks,metrics=metrics,gains=gains,receiving_audits=audits,
        identification=identification,flows=flows,packing=packing_audit(identification),
        validation_scope='Same observed seed23 state2400; train2400-2700, late2700-2850. Repeatedly inspected development data, not independent holdout.',
        cost_scope='East mainline plus four on/off connectors, not full Omega; original terminal zero-gradient boundary retained.')
    save(O/'validation.json',receipt)
    report(receipt)
    print(json.dumps(dict(forecasts=forecasts,metrics=[r for r in metrics if r['scope']=='fit_cells'],gains=gains,identification=identification),indent=2))


if __name__=='__main__':
    import sys
    main(sys.argv[1:])
