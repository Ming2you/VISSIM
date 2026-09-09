이 fixture는 원래 `evaluation/runs` 폴더와 과거 git history가 없는 checkout에서 관측·Ω·SC2001·strict runner 회귀를 실행하기 위한 자료입니다. VISSIM 실행이나 FZP 재생은 필요하지 않습니다.

`control_area_v1.zip`은 원본 run JSON/CSV **45개**와 고정 OFF 회귀용 git source blob **4개**를 포함합니다. 크기는 **5,564,491 bytes**이고 SHA256은 `26e5379f4ff4af54f11c7e19b236a7ac0dbefd4164660511dc5098a866d242f5`입니다. 각 원본의 byte 수와 SHA는 ZIP 안의 `index.json`에 있으며, 외부 `control_area_v1.manifest.json`이 압축 파일 자체의 SHA를 고정합니다. Git blob은 명시된 커밋의 source reference이며 실행 당시 기록된 raw 파일 SHA와 같다는 주장을 하지 않습니다.

Windows에서 다음 명령은 새 위치를 만들어 복원하고, 실제 production 함수와 fake-COM VBS/PowerShell 검사를 실행합니다.

```powershell
python -m diagnostics.run_portable_fixture_tests --include-wsh
```

VBS 검사를 제외하려면 `--include-wsh`를 생략합니다. VBS는 Windows Script Host 초기화가 가능한 환경에서 실행해야 하며 VISSIM COM은 생성하지 않습니다. Python 모델 검사에는 기존 프로젝트의 Python 의존성, vendor source, n7 config·mapping·pinned network 자료가 필요합니다. 추가 runtime 데이터는 `diagnostics/area_production_required_files.json`에 정리돼 있습니다.

복원은 새 `.review-fixtures/isolated-<id>` 안에만 이루어집니다. 기존 목적지가 있으면 실패하며 덮어쓰기·삭제는 하지 않습니다. `raw/`는 ZIP 원본 바이트를 그대로 보관합니다. `relocated/`의 JSON은 **문자열 전체가 기록된 workspace의 절대 경로일 때만** 현재 checkout 또는 복원된 run 위치로 연결합니다. 교통수치·차량 ID·run ID·source SHA·control은 바꾸지 않습니다. 모든 경로 변경의 JSON pointer, 이전값, 새값과 복원 파일 SHA는 `restoration.json`에 남습니다. 원본 run 파일은 수정하지 않습니다.

중앙 `fixture_path`는 활성화된 복원 위치에서만 과거 run 파일을 찾습니다. 요청한 파일이 ZIP에 없으면 원래 로컬 run으로 넘어가지 않고 정확한 누락 파일로 실패합니다. 고정 source reference도 ZIP에서 읽습니다. 검증 subprocess는 원래 checkout의 `evaluation/runs`에 대한 read/listdir와 `git` subprocess 호출을 금지하므로, 우연히 로컬 archive나 git history를 이용하면 검사 자체가 실패합니다.

미터 finalization 통합 후 실제 분리 실행 결과는 **49검사 PASS**입니다.

| 검사 묶음 | 수 |
|---|---:|
| raw SHA, 경로 변경만 존재, run ID, 재복원 거부, fallback 금지, Windows 경로 탈출 거부 | 6 |
| Ω635 관측 지원 | 5 |
| 실제 dynamic route와 원점 prior | 7 |
| SC2001 stock·geometry·accepted flow·Ω OFF·OFF reference·실제 미터 endpoint | 12 |
| 실제 observation projection | 9 |
| 실제 arrival path | 4 |
| 실제 watchdog/VBS strict ON·OFF·상속·child output | 6 |

Python43검사와 Windows strict6검사를 함께 실행하여 37.689초에 통과했습니다. 원래 run 접근 시도0, git source 호출 시도0입니다. 최신 결과는 `diagnostics/portable_fixture_validation.json`, 이전 Windows 단독 검사 기록은 `portable_fixture_validation_strict.json`에 있습니다. 새 미터 검사는 실제 150초 coupled endpoint에서 관측 문맥·입력 명령 불변·최종 차량 재고 closure를 확인합니다. 이 검증은 새 fixture 위치에서 production 코드를 실행한 검사이며 완전히 새 운영체제나 다른 Python 버전까지 검증한 것은 아닙니다. 다른 과거 분석 스크립트가 요청하는 run은 이 한정된 bundle에 없을 수 있습니다.

반복해서 사용할 기본 위치만 만들려면 다음 명령을 한 번 실행합니다.

```powershell
python diagnostics/review_fixtures.py
python -m unittest diagnostics.test_area_projection_coverage diagnostics.test_dynamic_area_routes diagnostics.test_sc2001_corridor diagnostics.test_observation_projection diagnostics.test_area_arrival_routes -v
```

기본 `.review-fixtures/control-area-v1`이 있으면 중앙 helper가 자동으로 사용합니다. 다른 복원 위치를 쓸 때는 `VISSIM_REVIEW_FIXTURE_ROOT` 환경변수로 해당 위치를 지정합니다. `.review-fixtures`는 재생성 가능한 로컬 자료이며 커밋하지 않습니다.

원본 archive를 재생성하는 명령은 `python -m diagnostics.build_review_fixture_archive`입니다. 이 작업에만 원래45파일과 해당 git history가 필요합니다. 이미 있는 ZIP을 덮어쓰지 않습니다. 배포·일반 테스트에는 archive 생성기를 실행할 필요가 없습니다.

별도 `receiver_turns_v1.zip`은 beta0 첫 실행의1050초 관측 누락 회귀용입니다. 원본 상태·직전900초 명령·기록 manifest와 현재 수선 입력을 사용하는 재현 설정, 총4개 파일을187,207 bytes로 보존합니다. SHA256은 `100c8a7ea99273a8359a485977da0406e59d7e87e56c425bac3af4b40a5e6c89`입니다. 기존 v1 archive와 기록은 교체하지 않습니다.

```powershell
python -m diagnostics.run_receiver_fixture_tests
```

새 위치에 복원한 뒤 원래 run 폴더 접근과 git 호출을 막은 subprocess에서 실제10421 단독 재고·초기 entry0, 수선 제거 시 원래 오류, 나머지29개 미확정 양수 차단을 확인합니다. 세 검사 PASS, 금지 접근0입니다. 전체31개 pure 상태 재고 검사 결과는 `projection_support_receiver_regression.json`에 별도로 남으며 이 작은 ZIP에31개 상태를 포함했다는 뜻은 아닙니다. 원본이 있을 때만 사용하는 archive 생성기는 `python -m diagnostics.build_receiver_fixture_archive`이며 기존 archive를 덮어쓰지 않습니다.
