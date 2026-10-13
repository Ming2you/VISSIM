"""Prepare one post-fix full decision; preserve the failed lazy attempt."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_bytes())
write=lambda p,d:p.write_text(json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
assert not (HERE/'hot_full_benchmark_plan.json').exists()
assert read(HERE/'hot_validation/comparison.json')['status']=='equivalent'
assert read(HERE/'hot_validation/execution.json')['status']=='complete_pending_comparison'
old=read(HERE/'lazy_benchmark_plan.json')
plan=dict(old,status='prepared_not_launched',launches_consumed=0,
    output=str(HERE/'hot_full'),reason='Post-fix full same-candidate lazy derivative benchmark. Event-count-only guard defect diagnosed, exact response/Jacobians verified; scalar stock packing disabled.',
    previous_failed_attempt='lazy_full',previous_failure_diagnosed='upgrade_replay/comparison.json',
    exact_response_validation='hot_validation/comparison.json',regression_tests=129,regression_subtests=24)
plan.pop('failure',None)
plan['arguments']=list(old['arguments'])
plan['arguments'][plan['arguments'].index('--out')+1]=str(HERE/'hot_full')
plan['arguments'][plan['arguments'].index('--tuning')+1]=str(HERE/'hot_config.json')
pins=read(HERE/'hot_validation/prepared.json')['source_pins']
changed=[]
for name,digest in list(pins.items()):
    path=Path(name)
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if actual!=digest:
        assert path==ROOT/'evaluation/controllers/sdmpc_stock_geometry.py',name
        changed.append(dict(path=name,before=digest,after=actual,reason='AD-only stock wrapping; scalar keeps original generator/assertions.'))
        pins[name]=actual
for path in (ROOT/'evaluation/controllers/sdmpc.py',ROOT/'evaluation/controllers/sdmpc_pfo.py',
             ROOT/'evaluation/controllers/sdmpc_tangent_surrogate.py',ROOT/'evaluation/controllers/sdmpc_tangent_worker.py',
             ROOT/'evaluation/controllers/sdmpc_stock_geometry.py',HERE/'hot_config.json',
             ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'):
    pins[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
plan['source_pins']=pins
plan['changes_since_exact_response_validation']=changed
write(HERE/'hot_full_benchmark_plan.json',plan)
source=(HERE/'run_lazy_once.ps1').read_text(encoding='utf8')
source=source.replace('lazy_benchmark_plan.json','hot_full_benchmark_plan.json').replace('lazy_dispatch.lock','hot_full_dispatch.lock').replace('lazy_full.','hot_full.')
# Same immutable source/input set must still hold after the actual child exits.
source=source.replace("    $done=Get-Content", "    foreach ($pin in $plan.source_pins.PSObject.Properties) {\n        if ((Get-FileHash -LiteralPath $pin.Name -Algorithm SHA256).Hash.ToLower() -ne $pin.Value) { throw \"Source changed while running: $($pin.Name)\" }\n    }\n    $done=Get-Content")
(HERE/'run_full_hot_once.ps1').write_text(source,encoding='utf8')
main=read(HERE/'plan.json')
main.update(status='prepared_full_lazy_hot_benchmark',tests=dict(passed=129,subtests=24),
    hot_validation=dict(status='equivalent',summary_and_route_amount_max_error=0.,all_jacobian_max_error=0.,
        scalar_seconds_before=59.32083800015971,scalar_seconds_after=73.74934650002979,
        ad_seconds_before=244.6338323999662,ad_seconds_after=226.44346070010215,
        scalar_followup='Keep original stock/assertion functions; geometry cache unchanged. Regression verified.'),
    full_benchmark='hot_full_benchmark_plan.json',
    next_after_selection='Read completed hot_full only once, compare all3 commands/costs/constraints/search budget with cache_on; do not claim600s before full completion.')
write(HERE/'plan.json',main)
outer=read(HERE.parent/'plan.json')
outer['runtime600_latest']=dict(status=main['status'],plan=str(HERE/'plan.json'),
    target_seconds=600,goal_complete=False,verified_complete_baseline_seconds=2006.4634451,
    new_native_runs=0,additional_coefficient_fits=0)
write(HERE.parent/'plan.json',outer)
with (HERE.parent/'README.md').open('a',encoding='utf8') as f:
    f.write('''\n\n### Runtime600: 同一候補の完全一致と全選択の再測定準備 (2026-10-09)\n\n- 同一候補のscalar/AD予測・経路時刻別量・主主体/資源/全物理状態Jacobianは完全一致（最大差0）。ADは244.63→226.44秒、scalarは59.32→73.75秒で悪化。全選択600秒達成の証拠ではない。\n- scalarでは効果のないAD用stock packingを除外し、元の集計・保存検査を維持した。129試験・24下位試験通過。450秒地平・候補・反復上限・物理モデルを変えず、遅延微分と合わせた新規一回の全選択をhot_fullへ準備。過去失敗lazy_fullは保存し再開しない。\n'''.replace('同一候補の完全一致と全選択の再測定準備','동일 후보 완전 일치·전체 선택 재측정 준비').replace('同一候補のscalar/AD予測・経路時刻別量・主主体/資源/全物理状態Jacobianは完全一致（最大差0）。ADは244.63→226.44秒、scalarは59.32→73.75秒で悪化。全選択600秒達成の証拠ではない。','동일 후보 scalar/AD 예측·경로/시간별 양·주체/자원/전체 물리상태 Jacobian 최대 차이0. AD는244.63→226.44초, scalar는59.32→73.75초로 악화했다. 전체 선택600초 달성 근거는 아니다.').replace('scalarでは効果のないAD用stock packingを除外し、元の集計・保存検査を維持した。129試験・24下位試験通過。450秒地平・候補・反復上限・物理モデルを変えず、遅延微分と合わせた新規一回の全選択をhot_fullへ準備。過去失敗lazy_fullは保存し再開しない。','scalar의 불필요한 AD용 stock packing을 제외하고 기존 집계/보존 검사를 유지했다.129시험/24하위시험 통과.450초 지평·후보·반복 상한·물리 모델을 유지하며 지연 미분을 합친 전체 선택1회를 hot_full에 준비했다. 실패 lazy_full은 보존하며 재개하지 않는다.'))
print(json.dumps(dict(status=plan['status'],pins=len(pins),output=plan['output'])))
