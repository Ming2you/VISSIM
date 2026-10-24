from pathlib import Path
import sys
import json
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine'), str(ROOT / 'diagnostics')]
from test_urban_flow_accounting import seed_all_inside
from src.models.state import ExperimentConfig, TrafficState, ControlAction
from src.models.demand import DemandStep
from src.controllers import rollout_endpoint as ep
from evaluation.controllers import area_runtime, vissim_stackelberg_adapter as adapter


def run():
    cfg = ExperimentConfig()
    cfg.simulation.control_interval = 20
    cfg.network.freeway_segments_per_link = 2
    cfg.network.freeway_segment_length_km = .25
    cfg.network.off_ramps = []
    cfg.network.control_area_enabled = True
    cfg.network.control_area_beta_seconds = 0
    state = TrafficState.initial(cfg)
    for link in cfg.network.freeway_links:
        state.freeway_density[link] = [0., 0.]
        state.freeway_speed[link] = [80., 80.]
    state.refresh_freeway_flow(cfg.network)
    seed_all_inside(state, cfg)
    area_runtime.install(adapter, cfg)
    rows = []
    for vsl in (40, 60, 80, 100, 120):
        control = ControlAction.uncontrolled(cfg)
        control.vsl = {k: vsl for k in control.vsl}
        result = ep.evaluate_price_point(state, control,
            [DemandStep({link: 7200. for link in cfg.network.freeway_links}, {}, {}) for _ in range(3)], [],
            ep.ObjectiveSpec(cfg, depth_override=3, abort_above=0))
        rows.append({'vsl': vsl, **{k: v for k, v in result.control_area.items() if k != 'flow_counts'}})
    return rows


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
