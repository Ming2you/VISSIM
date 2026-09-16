# 2026-09-16 다른 컴퓨터에서 재개

브랜치: `codex/control-full-review-20260909`

작업의 결론과 남은 일은 [최신 인계 문서](../../docs/HANDOFF_20260916_geometry_actuator_response.md)를 먼저 읽는다. 새 기하의 full GNE controller는 아직 지원하지 않는다. 완료된 native 4조건과 컴포넌트 예측을 재현하는 인계다.

## 가져오기와 자료 복원

저장소가 없는 컴퓨터에서는 다음과 같이 받는다. 기존 저장소가 있으면 로컬 변경을 보존하고 해당 브랜치를 갱신한다.

```powershell
git clone --branch codex/control-full-review-20260909 https://github.com/Ming2you/VISSIM.git
cd VISSIM
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --restore --verify
```

분할 파일은 하나의 ZIP 스트림이다. 각각 수동으로 압축을 풀지 않는다. 복원기는 파일별 SHA-256을 검사하며 다른 내용의 기존 파일이 있으면 쓰기 전에 중단한다. 기존 자료를 덮어쓰지 않는다. 복원 후 다음 명령으로 다시 확인할 수 있다.

```powershell
python -B -X utf8 diagnostics/handoff_20260916/restore_evidence.py --verify
```

`evidence_manifest.json`에 복원 경로·해시·분할 파일 해시·제외 파일을 기록했다. `git_paths.txt`는 이번 인계에서 명시적으로 고른 Git 파일이고 `direct_files.json`은 직접 저장한 파일의 해시다. 데이터는 중복 내용을 한 번만 압축하고 원래 경로로 복원한다.

포함 범위는 사용자 수정 망의 비원시 관측·예측·검증 결과, seed 13/17 자료, 성공/실패한 고정 명령 실행 기록, 동결 소스 ZIP, 정확한 INPX/SIG/배경 파일, 기존 rule baseline 자료다. 원시 `.fzp`, native `.db/.knr/.rsr`, 실행 캐시와 `.plot-deps`는 제외했다. 최근 실험의 원시 FZP만 약 8.7GB이며 원래 컴퓨터에 보존돼 있다. 따라서 이 패키지만으로 **오프라인 모델 예측과 기존 native 검증 결과 검토는 가능하지만, 원시 궤적을 다시 파싱하는 독립 검증은 불가능**하다. 그때는 원래 FZP를 별도 전송하거나 조율한 새 실험이 필요하다.

## 오프라인 재현

검증한 환경은 Windows, Python 3.12.14, NumPy 2.5.3이다. 그림 재생성에는 matplotlib 3.11.2도 사용했다. 원래 컴퓨터의 `.plot-deps`나 절대 경로를 복사할 필요는 없다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r diagnostics/handoff_20260916/requirements-offline.txt
python -B -X utf8 diagnostics/handoff_20260916/test_restore_evidence.py
python -B -X utf8 diagnostics/demand_sweep/user_native_20260914/metanet_terms_implementation_v2/test_profile_relocation.py
python -B -X utf8 diagnostics/demand_sweep/user_native_20260914/metanet_terms_implementation_v2/evaluate_native_response.py --experiment diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v3 --analysis diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v3/analysis/results_v1 --out diagnostics/demand_sweep/user_native_20260914/metanet_terms_implementation_v2/native_response_portable_recheck --ramp-local-step-sec 1
```

출력은 새 폴더로 지정하고 보존한 v1/v2 결과를 덮어쓰지 않는다. `--ramp-local-step-sec 1`이 이번 모델이다. 기본값 10초는 과거 결과 재현용이다. 위 명령은 복원한 관측만 사용하며 VISSIM이나 원시 FZP를 읽지 않는다.

과거 JSON의 절대 경로는 실행 출처로 남긴다. live harness는 현재 저장소 안에서 같은 SHA-256의 geometry profile만 찾아 사용하며, 기하 fingerprint 검사를 완화하지 않는다.

## 이후 VISSIM 실행

VISSIM 2020과 COM이 가능한 Windows에서 다른 실행과 조율한 뒤 시작한다. 이전 `prepared.json`은 원래 컴퓨터의 기록이므로 내용을 고쳐 재사용하지 않는다. 복원한 네트워크로 새 폴더에 prepare한다. 다음은 무제어 진단을 다시 실행할 때의 예시이며, 인계 작업에서는 실행하지 않았다.

```powershell
python -B -X utf8 diagnostics/fast_fixed_profile.py --network diagnostics/demand_sweep/user_native_20260914/east080_v1/prepared/network/baseline.inpx --profile diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v3/none.json --output diagnostics/native_recheck/prepared
& diagnostics/fast_nc_run.ps1 -Prepared diagnostics/native_recheck/prepared -Output diagnostics/native_recheck/run -Python (Get-Command python).Source -Execute
```

seed·수요·원래 신호·SimPeriod 9001을 유지하고 SimBreak 2250으로 끝낸다. 초기 300초 동안 실제 simulation 진행이 없을 때만 runner가 소유한 실행을 종료한다. 다른 사용자의 VISSIM을 일괄 종료하지 않는다.

## 검증 기록

임시 패키지 복원 시험과 geometry profile 이식 시험을 통과했다. 최종 별도 폴더 복원·모델 재실행 결과는 `TRANSFER_VALIDATION.md`에 기록한다.
