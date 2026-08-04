# G6 측정 결과를 plant/src/vissim_strict/shadow.py 가 먹는 JSONL 레코드로 변환하고 게이트를 판정한다.
"""shadow.py 재사용 계층.

shadow.py 는 **채점기**다. G6 세 지표(Spearman ρ / top-action pairwise / spillback F1)를
이미 정확히 구현하고 있으므로 지표를 다시 짜지 않는다. 없는 것은 **레코드 생산자**이고,
이 모듈이 그것이다.

shadow 레코드 계약에서 주의할 것 2개.

1. `shadow_mode=True`, `actuation_attempted=False` 가 강제된다. G6 하네스의 VISSIM
   집행은 컨트롤러의 actuation 경로가 아니라 **오프라인 분기 리플레이**(같은 시드로
   재실행 후 t0 에서 액션만 갈라놓기)이므로 이 선언은 사실과 부합한다.
2. `action_hash`/`policy_hash`/`build_hash`/`action_schema_hash` 는 전부 64자 hex 필수다.
   canonical-json SHA-256 으로 만든다(shadow 가 쓰는 것과 같은 직렬화).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any, Iterable, Mapping

VISSIM_ROOT = Path(__file__).resolve().parents[2]
PLANT_PKG_DIR = VISSIM_ROOT / "plant" / "src" / "vissim_strict"


def _load_plant_package() -> types.ModuleType:
    """plant 의 vissim_strict 를 별칭 패키지로 적재한다.

    `plant/src` 와 NumSim 의 `src` 는 **같은 최상위 패키지 이름 `src`** 를 쓴다.
    sys.path 에 둘 다 넣으면 먼저 import 된 쪽이 `sys.modules["src"]` 를 선점해
    다른 쪽 import 가 조용히 실패한다. 그래서 sys.path 를 건드리지 않고
    `vissim_strict_plant` 라는 별칭 패키지로 직접 적재한다.
    """

    name = "vissim_strict_plant"
    if name in sys.modules:
        return sys.modules[name]
    package = types.ModuleType(name)
    package.__path__ = [str(PLANT_PKG_DIR)]
    sys.modules[name] = package
    for module_name in ("topology", "shadow"):
        spec = importlib.util.spec_from_file_location(
            f"{name}.{module_name}", PLANT_PKG_DIR / f"{module_name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"{name}.{module_name}"] = module
        spec.loader.exec_module(module)
        setattr(package, module_name, module)
    return package


_plant = _load_plant_package()
shadow = _plant.shadow
RECORD_SCHEMA_VERSION = shadow.RECORD_SCHEMA_VERSION
evaluate_shadow_records = shadow.evaluate_shadow_records
write_report = shadow.write_report
canonical_json_sha256 = _plant.topology.canonical_json_sha256
PASS = shadow.PASS
FAIL = shadow.FAIL
NOT_EVALUATED = shadow.NOT_EVALUATED
load_jsonl = shadow.load_jsonl
spearman_rank_correlation = shadow.spearman_rank_correlation


def hash_payload(payload: Mapping[str, Any]) -> str:
    return canonical_json_sha256(dict(payload))


def file_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_record(
    *,
    decision_id: str,
    candidate_id: str,
    model_objective: float | None,
    vissim_objective: float | None,
    model_spillback: bool,
    vissim_spillback: bool | None,
    action_payload: Mapping[str, Any],
    policy_hash: str,
    build_hash: str,
    action_schema_hash: str,
    topology_hash: str,
    program_hash: str,
    state_hash: str,
    model_runtime_sec: float,
    decision_runtime_sec: float | None = None,
    status: str = "OK",
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "decision_id": decision_id,
        "candidate_id": candidate_id,
        "strict_predicted_objective": None if model_objective is None else float(model_objective),
        "strict_status": status,
        "strict_runtime_sec": float(model_runtime_sec),
        "action_hash": hash_payload(action_payload),
        "policy_hash": policy_hash,
        "build_hash": build_hash,
        "action_schema_hash": action_schema_hash,
        "topology_hash": topology_hash,
        "program_hash": program_hash,
        "state_hash": state_hash,
        "based_on_state_hash": state_hash,
        "strict_predicted_spillback": bool(model_spillback),
        "fallback_required": False,
        "fallback_event_logged": False,
        "silent_fallback": False,
        "shadow_mode": True,
        "actuation_attempted": False,
        "stale_fault_injection_observed": False,
        "fallback_fault_injection_observed": False,
        "readback_fault_injection_observed": False,
    }
    if vissim_objective is not None:
        record["vissim_observed_objective"] = float(vissim_objective)
    if vissim_spillback is not None:
        record["vissim_observed_spillback"] = bool(vissim_spillback)
    if decision_runtime_sec is not None:
        record["decision_runtime_sec"] = float(decision_runtime_sec)
    return record


def write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def evaluate_and_write(records: list[Mapping[str, Any]], report_path: Path) -> dict[str, Any]:
    report = evaluate_shadow_records(records)
    write_report(report_path, report)
    return report
