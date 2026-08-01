# FD 재적합 결과를 캘리브레이션 json 과 leaf tuning json 으로 배관하는 스크립트.
"""FD 재적합 결과 -> 캘리브레이션 v2 + leaf tuning 생성.

배경. 어댑터는 calibration 을 읽은 뒤 tuning 의 `calibration_override` 로 덮어쓴다
(vissim_stackelberg_adapter.py L3824-3826). 프로덕션 체인의 부모 tuning
`real_world_modi_pstack_adapter_v1_response_calibrated_20260721.json` 이
operational.network 에 120/30/6900 을 박아 두고 있어서, 캘리브레이션 파일만 갈아도
재적합값은 컨트롤러에 도달하지 못한다.

부모 tuning 은 zone4 등 진행 중인 남의 작업이 상속하는 파일이라 손대지 않는다.
대신 leaf tuning 을 새로 만들어 같은 키를 재적합값으로 다시 덮어쓴다.
deep_update 는 자식이 이기므로 leaf 가 부모의 stale override 를 무력화한다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit-json", required=True)
    ap.add_argument("--fit-key", default="primary",
                    help="fits 에서 채택할 키. 식별성 미달이면 alt_unconstrained 를 쓴다.")
    ap.add_argument("--base-calibration", required=True)
    ap.add_argument("--out-calibration", required=True)
    ap.add_argument("--parent-tuning", required=True,
                    help="leaf tuning 이 extends 할 부모 파일명(같은 디렉터리 기준 상대명).")
    ap.add_argument("--out-tuning", required=True)
    ap.add_argument("--calibration-version", required=True)
    args = ap.parse_args()

    fit = json.loads(Path(args.fit_json).read_text(encoding="utf-8"))
    chosen = fit["fits"][args.fit_key]
    v_free = round(float(chosen["v_free"]), 3)
    rho_crit = round(float(chosen["rho_crit"]), 3)
    shape_a = round(float(chosen["a"]), 4)
    cap_link = round(float(chosen["capacity_veh_h_link"]), 1)

    network_block = {
        "v_free_kph": v_free,
        "rho_crit_veh_km_lane": rho_crit,
        "desired_speed_shape_a": shape_a,
        "freeway_capacity_veh_h": cap_link,
    }

    calib = json.loads(Path(args.base_calibration).read_text(encoding="utf-8"))
    calib["calibration_version"] = args.calibration_version
    calib["status"] = "freeway_fd_refit_from_no_control_run_20260801"
    calib.setdefault("operational", {}).setdefault("network", {}).update(network_block)
    prov = calib.setdefault("provenance", {})
    prov["freeway_fd_refit"] = {
        "fit_json": str(Path(args.fit_json).resolve()),
        "fit_key": args.fit_key,
        "point_files": fit.get("inputs"),
        "point_count_used": fit.get("point_count_used"),
        "observed_capacity": fit.get("observed_capacity"),
        "coverage": fit.get("coverage"),
        "point_metrics": chosen.get("point_metrics"),
        "note": (
            "택시(class 70) VSL 편입 이후의 새 플랜트에서 재추출한 no-control FD 점군에 "
            "적합했다. 구 값(캘리브레이션 100/24/7600, 실효 tuning 120/30/6900)은 모두 무효다."
        ),
    }
    out_calib = Path(args.out_calibration)
    out_calib.write_text(json.dumps(calib, ensure_ascii=False, indent=1), encoding="utf-8")

    tuning = {
        "extends": args.parent_tuning,
        "name": Path(args.out_tuning).stem,
        "description": (
            "FD 재적합(20260801) 값을 컨트롤러까지 실제로 도달시키는 leaf tuning. "
            "부모 체인의 adapter_v1 이 calibration_override.operational.network 에 "
            "120/30/6900 을 박아 두어 캘리브레이션 파일이 무력화되고 있었다. "
            "부모는 zone4 등 진행 중 작업이 상속하므로 건드리지 않고, 여기서 같은 키를 "
            "재적합값으로 다시 덮어쓴다."
        ),
        "calibration_override": {
            "calibration_version": args.calibration_version,
            "operational": {"network": dict(network_block)},
        },
        "notes": [
            "이 파일의 operational.network 는 out-calibration 과 값이 같아야 한다. 배관용 미러다.",
            "desired_speed_shape_a 는 어댑터 calibration_to_config_overrides 에서 metanet_a_m 으로 간다.",
            f"출처 적합: {Path(args.fit_json).name} / fits.{args.fit_key}",
        ],
    }
    out_tuning = Path(args.out_tuning)
    out_tuning.write_text(json.dumps(tuning, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps({
        "network": network_block,
        "calibration": str(out_calib),
        "tuning": str(out_tuning),
        "fit_key": args.fit_key,
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
