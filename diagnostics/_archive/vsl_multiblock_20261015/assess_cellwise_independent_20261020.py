"""Assess frozen independent predictions and record the calibration handoff."""
import datetime,hashlib,json,math,os
from pathlib import Path
V=Path(__file__).resolve().parent
O=V/'cellwise_independent_20261020'
A=V/'outflow_followup_20261019'
PINS={}
def read(p):
    raw=p.read_bytes();PINS[str(p)]=hashlib.sha256(raw).hexdigest();return json.loads(raw.decode('utf-8-sig'))
def save(p,x):
    tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8');os.replace(tmp,p)
def save_text(p,s):
    tmp=p.with_name(p.name+'.tmp');tmp.write_text(s,encoding='utf8');os.replace(tmp,p)
def rmse(values):return math.sqrt(sum(x*x for x in values)/len(values))

def main():
    assert not (O/'assessment.json').exists(),'Reuse assessment'
    actual=read(A/'independent_approach.json')['rows']
    contrasts=[];absolute=[];baseline_parity=[]
    for seed in (67,71):
        closure=read(O/f'seed{seed}_owner_closure.json')
        assert closure['recorded_pid_absent'] and closure['actual_exit_code']==0
        summary=read(O/f'seed{seed}/summary.json')
        assert summary['new_predictions']==4 and summary['fits']==0
        for path,digest in summary['source_pins'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
        omega=read(Path(f'E:/VISSIM_analysis/20261011_vsl_response349/matched_seed{seed}_v3/matched_assessment.json'))['native_delta']['omega']
        arms=summary['arms']
        for variant in ('original','fitted'):
            left,right=[summary['results'][variant+'_'+arm] for arm in arms]
            for j,horizon in enumerate((150,300,450)):
                truth=next(r for r in actual if r['seed']==seed and r['horizon']==horizon)
                contrasts.append(dict(seed=seed,variant=variant,horizon=horizon,native_flow=truth['native_through18'],model_flow=right['throughflow'][j]-left['throughflow'][j],native_stock=truth['native_approach_n'],model_stock=sum(right['frames'][j]['n'][14:19])-sum(left['frames'][j]['n'][14:19]),native_omega=omega if horizon==450 else None,model_omega=right['ttt']-left['ttt'] if horizon==450 else None))
            for arm in arms:
                s=summary['results'][variant+'_'+arm]['scores']
                absolute.append(dict(seed=seed,arm=arm,variant=variant,**s,normalized_loss=s['n_rmse']**2/100+s['speed_rmse']**2/400))
        old=Path('E:/VISSIM_analysis/20261012_ramp_plant355')/('seed67_spatial360' if seed==67 else 'seed71_spatial')
        old_summary=read(old/'summary.json')
        for arm in arms:
            fresh=summary['results']['original_'+arm]
            before=old_summary['results'][arm]
            snaps=read(old/f'{arm}_snapshots.json')[1:]
            assert len(snaps)==3
            baseline_parity.append(dict(seed=seed,arm=arm,old_folder=str(old),ttt_abs_error=abs(fresh['ttt']-before['ttt']),
                max_n_abs_error=max(abs(a-b) for p,q in zip(fresh['frames'],snaps) for a,b in zip(p['n'],q['n']['FW_E'])),
                max_speed_abs_error=max(abs(a-b) for p,q in zip(fresh['frames'],snaps) for a,b in zip(p['speed'],q['speed']['FW_E']))))
    metrics={}
    for variant in ('original','fitted'):
        r=[x for x in contrasts if x['variant']==variant]
        scores=[x for x in absolute if x['variant']==variant]
        metrics[variant]=dict(mean_normalized_loss=sum(x['normalized_loss'] for x in scores)/len(scores),
            flow_delta_rmse=rmse([x['model_flow']-x['native_flow'] for x in r]),
            stock_delta_rmse=rmse([x['model_stock']-x['native_stock'] for x in r]),
            omega450_delta_rmse=rmse([x['model_omega']-x['native_omega'] for x in r if x['horizon']==450]))
    report=dict(status='independent_checks_complete_candidate_not_adopted',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        rows=contrasts,absolute=absolute,metrics=metrics,baseline_cache_parity=baseline_parity,
        independent_loss_reduction=1-metrics['fitted']['mean_normalized_loss']/metrics['original']['mean_normalized_loss'],
        new_forecasts=8,new_fits=0,native=0,production_edits=0,goal_complete=False,candidate_adopted=False,
        conclusion='This focused one-step correction is not a validated VSL-response repair. The three-cell fit is not a test of the impossibility of full cellwise calibration. Preserve all fitted values as development evidence; do not deploy.',
        limitations=['Both seeds excluded from coefficient fitting; earlier outcomes were seen, so not blind validation.',
          'Observed detector is inside connector, model flow at upstream face; previous location and integration limits retained.',
          'Endpoint stock is distinct from normal exit; no missing horizon Omega values were invented.',
          'No AD/NP/NUF optimization/policy/native performance qualification; all31-cell parameter identification remains incomplete.'],
        next='Before additional fitting, assess parameter identifiability and freeflow/congestion/recovery coverage across all31cells using preserved observations. Fit identifiable cell-specific FD/response parameters with shared priors and coupled trajectory/flow targets, preserving entire episodes/seeds for validation. Do not fit an artificial VSL bonus or retune on these two validation seeds.',source_pins=PINS)
    save(O/'assessment.json',report)
    text='''# 셀별 결합 보정 및 독립 검증 — 2026-10-20

현재 고속도로31개 셀은 이미 개별 계수를 갖는다. 마지막 기존 보정은 제한된 결합 방향과 비수렴 종료여서, 모든 셀의 계수가 충분히 식별됐다고 할 수 없다.

이번에는16–18번 셀 각각의 임계밀도·FD형상·속도완화·두 방향 예견계수, 총15개를 별도로 조정했다. 공간길이·450초 지평·FW5/U10·도시/램프 동역학·실제 도시/RM 명령·수요·목적함수는 고정했다.

1. 자유류/정체/회복이 포함된 기존1650/2250/2850초 시작의450초 궤적을 사용했다. 첫 최대25% 갱신은 종합오차를29.9% 키워 폐기했다. 이를 셀별 보정 자체의 실패로 해석하지 않았다.
2. 같은15개 민감도를 재사용해 최대5%로 줄인 한 번의 갱신은 학습 종합오차를3.53% 줄였다. 각 시간대 및 전체31셀의 재고·속도 유지조건과 물리보존을 통과했다. 아직 수렴한 보정은 아니다.
3. 계수를 고정하고 학습에 쓰지 않은seed67·71에서110/90 예측을 기존값과 비교했다. 과거 결과를 본 자료이므로 블라인드 검증이라고 하지 않는다.

| 조건 | 실제450초 통과량 변화 | 기존 예측 | 보정 예측 |
|---|---:|---:|---:|
'''
    development=read(V/'cellwise_smallstep_20261020/assessment.json')['development_response'][-1]
    text+=f"| seed29 두 구역90 | {development['native_flow']:+.0f}대 | {development['old_model_flow']:+.2f}대 | {development['candidate_model_flow']:+.2f}대 |\n"
    for seed in (67,71):
        base=next(r for r in contrasts if r['seed']==seed and r['variant']=='original' and r['horizon']==450)
        fit=next(r for r in contrasts if r['seed']==seed and r['variant']=='fitted' and r['horizon']==450)
        text+=f"| seed{seed} 기록된 VSL 조건 | {base['native_flow']:+.0f}대 | {base['model_flow']:+.2f}대 | {fit['model_flow']:+.2f}대 |\n"
    text+=f"\n독립 자료의 재고·속도 종합오차 변화는{report['independent_loss_reduction']*100:+.2f}% 개선이다(음수면 악화). 이 값은TTT 개선율이 아니다. VSL 반응 보정으로 생산 채택하지 않았으며, 모든 셀 보정이 끝났다는 주장도 하지 않는다.\n\n"
    text+='통과량 관측 위치와 모델 경계가 조금 다르다는 기존 한계를 유지한다. 실제 원점 삽입·도시/램프 영향과 전체ΩTTT는 서로 구분한다. 새VISSIM/FZP/전체SDMPC최적화/생산변경은0회다. 최초51예측, 작은 갱신4예측, 독립8예측을 재사용하며 다시 계산하지 않는다.\n\n다음은31셀 전체의 자료 범위와 식별 가능한 계수를 먼저 점검하는 작업이다. 셀별 계수는 허용하되, 정보가 적은 셀까지5개 계수를 모두 독립적으로 풀어 과적합시키지 않는다. 자유류 FD·정체 방출·회복 응답과 상하류 결합을 함께 맞추고, 검증용 에피소드는 보정에서 분리한다. 이번seed67·71에 다시 맞추지 않는다.\n'
    save_text(O/'README.md',text)
    for name in ('plan.json','summary.json'):
        p=V/name;x=read(p)
        x['cellwise_independent_20261020'].update(status=report['status'],forecasts=8,fits=0,assessment=str(O/'assessment.json'),readme=str(O/'README.md'),owner_closures=[str(O/f'seed{s}_owner_closure.json') for s in (67,71)],candidate_adopted=False)
        x['next']=report['next'];x['goal_complete']=False
        save(p,x)
    root_readme=V/'README.md'
    note='\n\n## 2026-10-20 셀별450초 결합 보정과 독립 검증 완료, 후보 미채택\n\n16–18번15계수의 첫25% 갱신은 학습오차29.9% 악화로 폐기했다. 민감도를 재사용한5% 갱신은 학습오차3.53% 개선했으나 VSL 반응은 해결하지 못했다. 계수를 고정한seed67/71 독립 예측8건도 완료했다. 새native/전체최적화/생산변경0, 각 소유정상종료 확인. [수치와 다음 작업](cellwise_independent_20261020/README.md). 실제 앱 목표는 마지막 조회BLOCKED 메타데이터이지만 사용자 승인에 따라 분석을 재개했으며, 목표완료를 주장하지 않는다.\n'
    save_text(root_readme,root_readme.read_text(encoding='utf8')+note)
    print(json.dumps(dict(metrics=metrics,independent_loss_reduction=report['independent_loss_reduction'],contrasts450=[r for r in contrasts if r['horizon']==450],baseline_cache_parity=baseline_parity),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
