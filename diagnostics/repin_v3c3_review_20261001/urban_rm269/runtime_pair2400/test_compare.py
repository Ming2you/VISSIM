"""Prevent a timing gain from hiding changed future controls or constraints."""
from copy import deepcopy
from pathlib import Path
import json

from diagnostics.repin_v3c3_review_20261001.urban_rm269.runtime_pair2400.compare import blocks, difference, inspect

OLD = Path(__file__).resolve().parent.parent/'selection2400'


def test_third_control_block_is_part_of_equivalence():
    action = json.loads((OLD/'unused.json').read_bytes())
    original = blocks(action)
    changed = deepcopy(original)
    changed[2]['diagnostics']['rw_meter_green_RM_C10681'] += 1
    differences = difference(original, changed)
    assert len(differences) == 1 and differences[0]['path'].startswith('/2/')
    assert not difference(original, blocks(action))


def test_small_numeric_noise_does_not_hide_feasibility_change():
    assert not difference({'cost': 500.}, {'cost': 500.+1e-10})
    assert difference({'feasible': True}, {'feasible': False})
    assert difference({'np': {'actual': 500.}}, {'np': {'actual': 501.}})


def test_completed_artifact_retains_nonconvergence_and_all_blocks():
    result = inspect(OLD, {'status': 'complete_uncompared', 'exit_code': 0,
                          'external_process_wall_sec': 1042.})
    assert len(result['action_blocks']) == 3
    assert not result['converged']
    assert result['selection_status'] == 'best_observed_feasible_sdmpc'
    assert result['query_stats']['failed_batches'] == 0
