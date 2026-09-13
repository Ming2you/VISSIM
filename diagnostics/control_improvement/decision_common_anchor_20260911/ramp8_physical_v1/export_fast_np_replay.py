"""Export already validated physical commands through the existing replay profile."""
import csv
import hashlib
import json
from pathlib import Path
import pickle
import sys

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]


def main():
    label = sys.argv[1]
    if not label.replace('_','').isalnum(): raise ValueError('Explicit completed record label required')
    stem = sys.argv[2] if len(sys.argv)>2 else label
    if not stem.replace('_','').isalnum(): raise ValueError('Fresh export stem required')
    receipt = json.loads((D/(label+'.json')).read_text(encoding='utf-8'))
    if not receipt['completed'] or receipt['source_changes']:
        raise ValueError('Incomplete or changed-source recorded qualification')
    raw = (D/(label+'.pickle')).read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt['result_pickle_sha256']:
        raise ValueError('Selected result pickle changed')
    from evaluation.controllers import vissim_stackelberg_adapter as a, action_csv_schema
    selected = pickle.loads(raw)['selected']
    if selected is None or selected['candidate_status'] != 'feasible_final_response':
        raise ValueError('No previously validated model-feasible selected command')
    response = selected['response']
    control = response['game']['control']
    token = hashlib.sha256(pickle.dumps(control,protocol=5)).hexdigest()
    if token != response['final_action_token'] or token != response['final_score']['action_token']:
        raise ValueError('Selected action is not its scored/written action')
    # Full cfg-sensitive validation happened at both candidate and leader
    # boundaries in the recorded solve. This export checks that receipt and
    # byte-exact action identity, and copies its existing ordered writer rows.
    rows = response['command_evidence']['ordered_rows']
    written_rows = []
    for row in rows:
        fields = str(row['metadata']).split(';')
        if fields[0] not in ('', 'ok'):
            raise ValueError('Unexpected source command status')
        details = dict(part.split('=',1) for part in fields[1:] if part)
        written_rows.append({**row, 'metadata':a._action_csv_metadata({'controller_status':'ok'},details)})
    action_path = D/(stem+'_selected_action.json')
    if action_path.exists(): raise FileExistsError(action_path)
    payload = a.control_to_json_dict(control,{'source_record':label,
        'finite_neighborhood_certified':response['game']['certified'],
        'model_quantity_constraints':response['final_score']['quantity_constraints'],
        'native_execution_certified':False})
    action_path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with action_path.with_suffix('.csv').open('w',newline='',encoding='utf-8') as stream:
        writer = csv.DictWriter(stream,fieldnames=action_csv_schema.ACTION_CSV_FIELDS)
        writer.writeheader(); writer.writerows(written_rows)
    offsets = {}
    for row in rows:
        if row['kind'] != 'signal_sg': continue
        owner = 'SC'+str(int(float(row['sc_no'])))
        value = float(row['offset'])
        if owner in offsets and offsets[owner] != value: raise ValueError('Inconsistent owner offset')
        offsets[owner] = value
    if len(offsets) != 17: raise ValueError('Incomplete physical SG owner catalog')
    config = json.loads((D/'vsl100_e0_replay1350_config_v1.json').read_text(encoding='utf-8'))
    config['name'] = stem+'_physical_replay1350'
    config['description'] = 'Fixed physical commands from the bounded recorded-state follower result; incomplete Nash gaps remain explicit.'
    spec = config['diagnostic']['signal_profile']
    spec.update(green_action_json=str(action_path.relative_to(ROOT)),
        green_action_sha256=hashlib.sha256(action_path.read_bytes()).hexdigest(),
        source_action_csv=str(action_path.with_suffix('.csv').relative_to(ROOT)),
        source_action_csv_sha256=hashlib.sha256(action_path.with_suffix('.csv').read_bytes()).hexdigest(),
        base_writer_offsets_sec=offsets, relative_offset_sec={},green_delta_sec={},replay_recorded_vsl=True)
    # The currently pinned profile has no NP/NUF metadata replay support. No
    # unsupported option is silently supplied. Physical CSV equality is the
    # criterion here; logical target replay is separately pending and unclaimed.
    config_path = D/(stem+'_replay1350_config.json')
    config_path.write_text(json.dumps(config,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    report = {'completed':True, 'source_record':label,'selected_action_token':token,'physical_rows':len(rows),
        'target_np_veh':control.N_P_star,'target_nuf_veh_h':control.N_UF_star,
        'finite_neighborhood_certified':response['game']['certified'],
        'logical_targets_replayed':False,
        'physical_columns_unchanged':all({k:v for k,v in row.items() if k!='metadata'}=={k:v for k,v in written.items() if k!='metadata'} for row,written in zip(rows,written_rows)),
        'metadata_status':'Canonical CSV status ok for the validated physical/model command; empty callback status replaced only through _action_csv_metadata. No GNE certificate.',
        'scope':'Physical-command replay only; NP/NUF source metadata remains in selected JSON and is not a native actuator. The pinned replay profile will report zero targets; this must be recorded as a metadata mismatch, not full action equality.',
        'action_json':str(action_path),'config':str(config_path)}
    (D/(stem+'_replay_export.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__': main()
