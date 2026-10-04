"""Assess saved initializer probes; no rollout, native run, or large-data scan."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIGIN = 'in_SC1004_S'

def load(name):
    return json.loads((HERE / (name + '.json')).read_bytes())

def total_stock(snapshot):
    return math.fsum(math.fsum(row.values()) for row in snapshot['stock_assignment'].values())

def without(mapping, keys):
    return {k: v for k, v in mapping.items() if k not in keys}

old = load('before4050')
new = load('after4050')
old3900 = load('before3900')
new3900 = load('after3900')
assert not old['completed']
assert old['error']['message'] == 'Kinematic queue definition differs from original physical queue'
assert new['completed'] and old3900['completed'] and new3900['completed']
assert old3900['before'] == new3900['before']
assert old3900['after'] == new3900['after']
assert old3900['metadata'] == new3900['metadata']

before, after = old['before'], new['after']
assert total_stock(before) == total_stock(after) == 3117.
assert math.fsum(before['support'].values()) == math.fsum(after['support'].values()) == 195.
assert math.fsum(before['queues'].values()) == 129.
assert math.fsum(after['queues'].values()) == 0.
assert after['support']['storage:' + ORIGIN] == 195.
assert before['storage'] - after['storage'] == 129.
# urban_link_storage stores FREE capacity. Occupied stock changes by its negative.
delta_occupied = -(math.fsum(after['all_storage'].values()) - math.fsum(before['all_storage'].values()))
delta_queue = math.fsum(after['all_queue'].values()) - math.fsum(before['all_queue'].values())
assert abs(delta_occupied + delta_queue) < 1e-8
assert without(before['stock_assignment'], {'66'}) == without(after['stock_assignment'], {'66'})
assert without(before['all_storage'], {ORIGIN}) == without(after['all_storage'], {ORIGIN})
assert without(before['all_queue'], set(before['queues'])) == without(after['all_queue'], set(after['queues']))
for field in ('all_arrival', 'all_release', 'tags'):
    assert without(before[field], {ORIGIN}) == without(after[field], {ORIGIN})
assert after['arrival'] == after['release']
assert math.fsum(after['arrival'].values()) == 195.
assert math.fsum(math.fsum(row.values()) for row in after['tags'][ORIGIN].values()) == 195.
assert new['metadata']['kinematic_arrivals'][ORIGIN]['future_traffic_inputs'] is False
assert total_stock(new['before']) == total_stock(after)
for path, digest in new['source_sha256'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
stop = Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
stop_sha = hashlib.sha256(stop.read_bytes()).hexdigest()
assert stop_sha == '91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'

result = dict(
    status='INITIALIZATION_FIXED_NOT_GAIN_QUALIFIED',
    at4050=dict(old_error=old['error'], new_completed=True, physical_link_stock=195,
        ready_queue_before=129., ready_queue_after=0., residual_before=66., residual_after=195.,
        all_projected_urban_stock_before=total_stock(before), all_projected_urban_stock_after=total_stock(after),
        occupied_storage_change=delta_occupied, movement_queue_change=delta_queue,
        physical_stock_change=delta_occupied + delta_queue, paired_arrival_release_veh=195,
        last_arrival_delay_sec=new['metadata']['kinematic_arrivals'][ORIGIN]['last_arrival_delay_sec'],
        unrelated_ledgers_unchanged=True),
    at3900=dict(before_initialization_exact=True, after_initialization_exact=True, kinematic_metadata_exact=True),
    scope='Existing kinematic-contract links only (current contract: 66); other projections retain prior behavior.',
    verification_limit='Saved full initialization, not autonomous rollout/SDMPC selection/native execution after this patch.',
    assessment_correction='An initial unsaved assessment incorrectly added free capacity to movement queue. That assertion failed. The corrected assessment uses the physical stock ledger and minus free-capacity change plus queue change; no production change was made for that diagnostic error.',
    new_rollouts=0, new_native_runs=0, future_traffic_inputs=False, stop_sha256=stop_sha,
    input_sha256={str(HERE / (n+'.json')):hashlib.sha256((HERE/(n+'.json')).read_bytes()).hexdigest()
                  for n in ('before4050','after4050','before3900','after3900')},
    source_sha256=new['source_sha256'])
(HERE/'initialization_assessment.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','input_sha256')}))
