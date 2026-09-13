"""Replay completed online counters through the consumer only; no model/native."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import signal_head_observation as observer

D = Path(__file__).resolve().parent
RUN = "codex_physical8_fw080_u050_fastnp_closedloop1350_v3"
DECISIONS = ROOT / "evaluation/runs" / RUN / ("decisions_" + RUN)
CONTRACT = D / "head_free_service_10565_v1.json"
MOVEMENT = "SC1005_N_SC105_to_W_SC1004"
OPTIONS = {"enabled": True, "min_green_sec": 30, "min_crossings": 5}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    started = time.perf_counter()
    states = {n: DECISIONS / f"state_{n:06d}.json" for n in [750, 900, 1050, 1200, 1350]}
    previous_actual = DECISIONS / "action_000750.json"
    origin = read(D / "sc1005_service_capacity_origin_v1.json")["observed_effective_movement"]
    document = read(CONTRACT)
    sources = [Path(__file__), Path(observer.__file__), ROOT / "diagnostics/test_head_free_service.py", CONTRACT,
               D / "sc1005_service_capacity_origin_v1.json", previous_actual, *states.values(),
               ROOT / document["network"]["path"], ROOT / document["movement_join"]["path"]]
    pins = {str(p.relative_to(ROOT)): digest(p) for p in sources}
    raw = {n: read(p) for n, p in states.items()}
    tuning = {"execution": {"native_signal_record": True}, "urban": {"capacity": {
        "head_observation": OPTIONS, "head_free_service": str(CONTRACT.relative_to(ROOT))}}}

    def consume(n, previous):
        cfg = SimpleNamespace(network=SimpleNamespace(
            urban_movements={MOVEMENT: {**deepcopy(origin["spec"]), "unsignalized": True}},
            urban_link_storage_veh={"SC1005_to_SC1004": 1.0},
            movement_capacity_veh_h=origin["capacity_veh_h"],
            movement_capacity_by_movement_veh_h={MOVEMENT: origin["capacity_veh_h"]}))
        observer.configure_head_free_service(cfg, tuning, raw[n])
        metadata = observer.install(cfg, raw[n], previous, dict(cfg.network.movement_capacity_by_movement_veh_h),
                                    {}, lambda *_: None, OPTIONS)
        window = raw[n]["local_observation"]["signal_observation_window"]
        return metadata, {"snapshot_sec": n, "window_sec": [window["start_sec"], window["end_sec"]],
            "confirmed_count": window["bypass_link_exits"].get("403", 0),
            "unknown_source_events": window["unknown_links"].get("403", 0),
            "inherited_service_veh_h": origin["capacity_veh_h"],
            "selected_service_veh_h": cfg.network.movement_capacity_by_movement_veh_h[MOVEMENT],
            **cfg.network.head_free_service["observations"]["10565"]}

    def envelope(folder, n, metadata):
        path = folder / f"consumer_metadata_{n}.json"
        path.write_text(json.dumps({"run_provenance": raw[n]["run_provenance"],
                                   "metadata": {"sim_sec": n, **metadata}}), encoding="utf-8")
        return path

    with tempfile.TemporaryDirectory(prefix="head_free_consumer_") as temporary:
        folder = Path(temporary)
        chronological, previous = [], None
        for n in states:
            metadata, row = consume(n, previous)
            chronological.append(row)
            previous = envelope(folder, n, metadata)
        metadata, first900 = consume(900, previous_actual)
        _, conditional1050 = consume(1050, envelope(folder, 900, metadata))
    assert chronological[0]["observed_only_floor_veh_h"] == 0
    assert chronological[1]["observed_only_floor_veh_h"] == 3600 * min(13, 17) / 150
    assert first900["observed_only_floor_veh_h"] == 0
    assert conditional1050["observed_only_floor_veh_h"] == 3600 * min(17, 13) / 150
    result = {"schema": "completed-online-head-free-consumer-evidence/v1", "completed": True,
        "native_run": False, "model_rollouts": 0, "fzp_reads": 0, "run": RUN,
        "scope": "Consumer-only replay of immutable completed online counters. Temporary metadata envelopes are not executed actions and are deleted. No historical state/action is changed.",
        "method": "Validated unique403L1->10565->58 and merged W aliases; direct-confirmed subset / complete elapsed window. Existing min exposure/count thresholds; min two contiguous windows, carry only same run/source/contract. Unknown transitions stay unassigned; source-wide stock is not saturation evidence.",
        "chronological_counter_replay": chronological,
        "first_activation_recorded900_with_actual_legacy_action750": first900,
        "conditional_recorded1050_after_new_consumer_metadata900": conditional1050,
        "initial_native_requirement": "A new run must collect and preserve two valid adjacent pre-control windows; historical action750 has no new consumer candidate so first activation at900 alone must not install312.",
        "source_sha256": pins, "source_changes": [p for p, sha in pins.items() if digest(ROOT / p) != sha],
        "elapsed_sec": time.perf_counter() - started}
    if result["source_changes"]:
        raise RuntimeError("Consumer evidence sources changed during replay")
    output = D / "head_free_service_evidence_v1.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "elapsed_sec": result["elapsed_sec"],
        "chronological_rates": [r["selected_service_veh_h"] for r in chronological],
        "first900": first900["selected_service_veh_h"], "conditional1050": conditional1050["selected_service_veh_h"]}))


if __name__ == "__main__":
    main()
