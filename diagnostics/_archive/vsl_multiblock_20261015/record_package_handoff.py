import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_bytes())
save=lambda p,v:Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=read(HERE/'plan.json')
plan['updated_utc']=datetime.now(timezone.utc).isoformat()
plan['status']='search_verified_compact_native_package_copy_running'
plan['constraints']['full_optimizations_this_stage']=1
plan['next_stage'].update(status='compact_package_copy_running',
    native_source='D:/VISSIM_packages/vsl_multizone355_20261015',
    original_source_preserved='E:/VISSIM_workspaces/vsl349_causal_20261011',
    preparation_script=str(HERE/'prepare_multizone.py'),
    preparation_script_sha256=sha(HERE/'prepare_multizone.py'),
    prepared_native_protocol='D:/VISSIM_packages/vsl_multizone355_20261015/diagnostics/sdmpc_n31_20260924/integration_20260926/native_vsl_multizone2250/protocol.json',
    matched_model_forecasts_budget=3,matched_model_forecasts_started=0,
    preflight_started=0,freeze_count=0,native_launches=0)
plan['next']='Follow package_copy_launch.json first. Wait for exact copy owner exit plus native_package_receipt.json before preparation. Do not rerun exporter. Then prepare_multizone.py once: canonical writer, exact native prefix, same city/RM and DSD59..66 only90; three matched355 forecasts. If an error occurs preserve and diagnose, never repeat completed predictions or native attempts. Canonical preflight and freeze are still pending. Runtime/native not launched. Search full selection and its2 exact checks are complete.'
save(HERE/'plan.json',plan)
save(HERE/'package_copy_launch.json',dict(pid=32548,creation_utc='2026-10-15T07:44:15.3981700Z',
    script=str(HERE/'prepare_native_package.py'),script_sha256=sha(HERE/'prepare_native_package.py'),
    command=['--install','--resume-verified-copy'],source=plan['next_stage']['original_source_preserved'],
    destination=plan['next_stage']['native_source'],expected_success_receipt=str(HERE/'native_package_receipt.json'),
    expected_files=54742,expected_bytes=1648654402,original_source_bytes=49454799555,
    reason='Whole source49.45GB exceeds D free46.53GB. Reuse existing solo355 compact runtime export; canonical whole-package freeze unchanged.',
    prior_copy_failure='Windows MAX_PATH before completion. First script preserved as prepare_native_package_failed_pathlength.py; partial equal bytes retained, long-path support added. No native/freeze attempts consumed.',
    native_runs=0,freeze_count=0,restart_automatically=False))
save(HERE/'full_selection_owner_closure.json',dict(pid=46876,creation_utc='2026-10-15T07:16:22.6994592Z',
    checked_utc=datetime.now(timezone.utc).isoformat(),owner_cim_absent=True,
    completion=str(HERE/'full_selection3300/completion.json'),exact_check_exit_code=0,
    exact_setup_failure_preserved=str(HERE/'exact_selected3300/failure_preserved.json'),
    corrected_cause='SDMPC deep-copies follower/state/config at solve entry. Exact validation now captures its configure_operating_bounds context; first attempt stopped before prediction.',
    successful_exact_predictions=2,full_selection_runs=1))
with (HERE/'README.md').open('a',encoding='utf8') as f:
    f.write('\n## 실행 준비 인계\n\n'
        '선택 명령의 이산 실행모델 ΔTTT는 유지 명령 대비−0.790899대·시간이며 VSL은110이었다. 이는 다른 제어수단을 포함한 모델 내부 선택 결과이고 native 개선이 아니다. 검증 초기의 설정 객체 동일성 검사는 solve 내부 deep copy를 고려하지 않은 검증 코드 오류였으며, 예측 전 중단 자료를 보존하고 올바른 private context에서2예측을 완료했다.\n\n'
        '원본49.45GB는D여유46.53GB를 초과했다. 기존 solo355 소형 패키징 정책으로 코드·실행입력1.65GB를 별도D패키지에 복사/해시 확인 중이며 원본과 과거 결과를 삭제하지 않았다. 복사 첫 시도의 Windows긴경로 오류와 스크립트를 보존했고, 기존 복사분의 해시를 확인하며 이어간다. 정확한 소유정보는package_copy_launch.json, 완료조건은native_package_receipt.json이다. 아직 정본 사전검사·동결·새native는0회다.\n')
print(plan['status'])
