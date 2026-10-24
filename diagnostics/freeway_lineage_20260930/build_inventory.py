"""Build a documentation snapshot only. No simulation, calibration, or git write."""
from pathlib import Path
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
I = Path('diagnostics/sdmpc_n31_20260924/integration_20260926')
C = I/'baseline_reproduction_20260929/cellwise_calibration'
F = C/'freeway_first'
E = I/'expanded036_9000_20260930'

sources = [I/'SELECTION.md', C/'README.md', C/'RESULT.md', C/'COVERAGE_REVIEW.md',
           C/'parameter_spec.json', C/'selected_coefficients.json', C/'summary.json', C/'verification.json']
for name in ['RESULT.md','selection.json','response_decomposition.json','summary.json']:
    sources.append(C/'jacobian_step'/name)
for name in ['README.md','protocol.json','summary.json','verification.json','selection.json',
             'effective_coefficients.json','control_flow_decomposition.json',
             'eval_036/reference_config.json','eval_036/manifest.json']:
    sources.append(C/'expanded_joint'/name)
for name in ['README.md','candidate_config.json','candidate_manifest.json','protocol.json',
             'effective_parameters.json','comparison.json','selection_comparison.json','final_verification.json']:
    sources.append(C/'coupled_expanded_joint'/name)
for name in ['README.md','RUNTIME_TRANSFER_AUDIT.md','route_inventory/README.md',
             'route_inventory/EARLY_CHECKS.md','route_inventory/s61_late/README.md',
             'connected_fd/README.md','connected_exit_drop/README.md',
             'regional_joint/README.md','regional_joint/FLOW_RESPONSE_REVIEW.md',
             'regional_joint/local_sensitivity.json',
             'inlet_speed_boundary/README.md','inlet_speed_boundary/verification.json']:
    sources.append(F/name)
for name in ['RM2700_FINDINGS.md','meter2700_decomposition.json','meter2700_integrity.json',
             'SOURCE_CELL_FINDINGS.md']:
    sources.append(E/name)

spec = json.loads((ROOT/C/'parameter_spec.json').read_bytes())['variables']
values = json.loads((ROOT/C/'expanded_joint/effective_coefficients.json').read_bytes())
effective = json.loads((ROOT/C/'coupled_expanded_joint/effective_parameters.json').read_bytes())['FW_E']
initial = {(x['cell'],x['parameter']):x['initial'] for x in spec}
assert len(values) == len(initial) == 159
rows = []
for x in values:
    cell, parameter, value = x['cell'], x['parameter'], x['value']
    segment = effective['segment_params'][cell]
    response = effective['state_response']['cell_overrides'][str(cell)]
    if parameter in ('rho_crit','metanet_a_m'):
        actual = segment[parameter]
    elif parameter == 'tau_sec':
        actual = response['relaxation']['acceleration_sec']
        assert actual == response['relaxation']['deceleration_sec']
    elif parameter in ('nu_ge','nu_lt'):
        actual = response['anticipation']['downstream_ge_local' if parameter=='nu_ge' else 'downstream_lt_local']
    elif parameter == 'delta_merge':
        actual = response['delta_merge']
    else:
        raise ValueError(parameter)
    assert abs(actual-value) < 1e-10, (cell,parameter,actual,value)
    before = initial[(cell,parameter)]
    rows.append(dict(cell=cell,parameter=parameter,initial=before,expanded036=value,
                     change=value-before,relative_change=(value-before)/before))
csv_path = HERE/'expanded036_parameters.csv'
with csv_path.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
by_cell = {i:{r['parameter']:r['expanded036'] for r in rows if r['cell']==i} for i in range(31)}
md = ['# expanded036 동측31셀 실효 계수', '',
      '159개 보정값을 전체망 `effective_parameters.json`과 대조했다. 모두 일치한다. 숫자는 표시할 때만 반올림한다.', '',
      '셀 번호는 0기준. ρcrit는 대/km/차로, τ는 초, ν는 km²/h다. ρcrit는 방향 배율 1.4가 이미 적용된 실효값이다. τ는 이 보정에서 가속/감속에 같은 값을 쓴다. δ가 빈칸인 셀은 새 합류 계수 보정 대상이 아니다.', '',
      '[초기값·최종값·변화량 CSV](expanded036_parameters.csv) · [계보 설명](../../docs/FREEWAY_MODEL_LINEAGE_20260930.md)', '',
      '|셀|ρcrit|a|τ [s]|νge|νlt|δmerge|', '|---:|---:|---:|---:|---:|---:|---:|']
for i,x in by_cell.items():
    vals=[f'{x[k]:.6f}' for k in ('rho_crit','metanet_a_m','tau_sec','nu_ge','nu_lt')]
    vals.append(f"{x['delta_merge']:.6f}" if 'delta_merge' in x else '—')
    md.append('|'+str(i)+'|'+'|'.join(vals)+'|')
(HERE/'EXPANDED036_PARAMETERS.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
sources += [Path('docs/FREEWAY_MODEL_LINEAGE_20260930.md'),
            csv_path.relative_to(ROOT),(HERE/'EXPANDED036_PARAMETERS.md').relative_to(ROOT),
            Path(__file__).relative_to(ROOT)]
records=[]
for rel in sources:
    data=(ROOT/rel).read_bytes()
    assert len(data)<2_000_000,rel
    if rel.suffix=='.json':json.loads(data)
    records.append(dict(path=rel.as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
assert len({x['path'] for x in records})==len(records)
total=sum(x['bytes'] for x in records)
assert total<5_000_000,total
inventory=dict(schema='freeway-model-lineage-evidence/v1',date='2026-09-30',
    scope='Documentation, parameter snapshots and compact completed evidence; not a self-contained executable runtime.',
    code_base='886a014a',current_native_model='coupled_expanded_joint / expanded_joint eval036',
    current_tuning_sha256='c4abfccb63110bb4f7458a666d5e87b7ae367a07c12ae8403169ec3d674ce6dc',
    network_sha256='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc',
    gain_qualified=False,native9000_complete_at_snapshot=False,
    effective_coefficients_checked=159,total_evidence_bytes=total,files=records)
(HERE/'inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(files=len(records)+1,bytes=total,coefficients_checked=159)))
