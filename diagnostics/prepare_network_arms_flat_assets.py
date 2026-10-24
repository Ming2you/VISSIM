"""Prepare one flat three-INPX experiment with shared SIG/JPG assets.

Stdlib only. Run later, after the parent's performance trace: this command
reads/copies the 95 MB image. No COM, model imports, original writes or overwrite.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / 'diagnostics/fixed_beta300v3_network_arms_v1'
V1_SHA = '18322b5ca49afe57b59baf271afdc8a3fc1cd850b711f2027afdedd656846030'
VALIDATION = ROOT / 'diagnostics/native_settings_validation.json'
VALIDATION_SHA = '6924c384ebdcb53717a31f4ad829e769b0bd557f9140119366e81eb82e0cef81'
SOURCE_NETWORK = ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
SOURCE_SHA = '085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317'
IMAGE = '개포동 Test-bed.jpg'
ARM_NAMES = ('baseline', 'lcd10635_2000', 'upstream1135')
DEFAULT_OUTPUT = ROOT / 'diagnostics/fixed_beta300v3_network_arms_flat_v1'
CHUNK = 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(CHUNK), b''):
            h.update(chunk)
    return h.hexdigest()


def basename(name):
    require(isinstance(name, str) and name not in ('', '.', '..') and not any(c in name for c in '/\\:#'), 'Unsafe flat asset name')
    return name


def relative(path):
    return path.resolve().relative_to(ROOT).as_posix()


def metadata(path):
    stat = path.stat()
    return (stat.st_size, stat.st_mtime_ns, stat.st_ino)


def checked_bytes(path, expected):
    raw = path.read_bytes()
    require(digest(raw) == expected.lower(), 'Source hash mismatch: '+str(path))
    return raw


def output_path(value):
    path = Path(value)
    path = (path if path.is_absolute() else ROOT/path).resolve()
    base = (ROOT/'diagnostics').resolve()
    require(path != base and path.is_relative_to(base), 'Output must be a separate diagnostics subtree')
    require(not path.is_relative_to(V1.resolve()), 'Cannot write inside preserved v1')
    require(not path.exists(), 'Output already exists; use a new directory, never overwrite')
    return path


def write_small(target, name, raw):
    path = (target/basename(name)).resolve()
    require(path.parent == target, 'Destination escaped flat directory')
    with path.open('xb') as stream:
        stream.write(raw)
    require(path.read_bytes() == raw, 'Destination byte readback mismatch: '+name)
    return {'destination':name, 'destination_sha256':digest(raw), 'size':len(raw)}


def copy_image_once(source, target):
    """One source read/copy; separately hash destination to verify copied bytes."""
    before = metadata(source)
    require(before[0] == 95065685, 'Reviewed background image size changed')
    h, count = hashlib.sha256(), 0
    path = (target/IMAGE).resolve()
    require(path.parent == target and source.resolve() != path, 'Invalid image destination')
    with source.open('rb') as reader, path.open('xb') as writer:
        for chunk in iter(lambda: reader.read(CHUNK), b''):
            writer.write(chunk)
            h.update(chunk)
            count += len(chunk)
    require(metadata(source) == before and count == before[0], 'Image source changed while copying')
    copied_sha = h.hexdigest()
    require(file_digest(path) == copied_sha, 'Image destination hash mismatch')
    return {'source':relative(source), 'source_sha256':copied_sha,
            'destination':IMAGE, 'destination_sha256':copied_sha, 'size':count,
            'source_hash_scope':'Captured during this copy, not a historical v1 image hash',
            'source_metadata_unchanged_during_copy':True, 'source_read_passes':1}


def prepare(target):
    target = output_path(target)  # Preserve the CLI safety gate for direct calls too.
    manifest_raw = checked_bytes(V1/'manifest.json', V1_SHA)
    validation_raw = checked_bytes(VALIDATION, VALIDATION_SHA)
    manifest, validation = json.loads(manifest_raw), json.loads(validation_raw)
    require(manifest['schema']=='fixed-command-route-network-arms/v1', 'Unexpected v1 schema')
    require(manifest['source_network_sha256']==SOURCE_SHA, 'Wrong original network')
    require(validation['status']=='complete' and validation['original_native_settings_exact'] is True,
            'Original COM setting gate absent')
    require(validation['run_ready'] is False, 'Unexpected native sidecar readiness')
    native_inputs = {str((ROOT/x['path']).resolve()):x for x in validation['inputs']}
    require(native_inputs[str((V1/'manifest.json').resolve())]['sha256']==V1_SHA, 'Sidecar not linked to v1')
    original = checked_bytes(SOURCE_NETWORK, SOURCE_SHA)
    require(set(manifest['arms'])==set(ARM_NAMES), 'Arm set changed')
    inputs = [{'path':relative(V1/'manifest.json'),'sha256':V1_SHA},
              {'path':relative(VALIDATION),'sha256':VALIDATION_SHA},
              {'path':relative(SOURCE_NETWORK),'sha256':SOURCE_SHA},
              {'path':relative(Path(__file__)), 'sha256':file_digest(Path(__file__))}]
    # Verify the saved original native evidence without invoking COM or runtime.
    for name in ('routes.csv','manifest.json'):
        path = ROOT/'diagnostics/routing_lookahead_native_readback_v1'/name
        row = native_inputs[str(path.resolve())]
        checked_bytes(path, row['sha256'])
        inputs.append({'path':relative(path),'sha256':row['sha256']})
    networks, refs = {}, {}
    for arm in ARM_NAMES:
        row = manifest['arms'][arm]
        source = (V1/row['network']).resolve()
        require(source.is_relative_to(V1.resolve()), 'v1 network path escaped')
        raw = checked_bytes(source, row['network_sha256'])
        require(len(raw)==row['network_size'], 'Arm size mismatch')
        networks[arm] = (source, raw)
        tree = ET.fromstring(raw)
        refs[arm] = [{'tag':node.tag,'no':node.get('no'),'attribute':key,'raw_reference':value,
                      'shared_filename':basename(value[6:])}
                     for node in tree.iter() for key,value in node.attrib.items() if value.startswith('#data#')]
        require(refs[arm] == refs[ARM_NAMES[0]], 'Experimental arm changed #data# references')
    require(networks['baseline'][1] == original, 'Baseline differs from original bytes')
    sig_names = {basename(x['copied_relative_path']) for x in manifest['relative_sig_references']}
    require(len(sig_names)==42, 'Expected exactly 42 common SIG assets')
    require({x['shared_filename'] for x in refs['baseline']}==sig_names|{IMAGE}, 'Unreviewed #data# dependency')
    sigs, sig_sources = {}, {}
    for name in sorted(sig_names):
        copies = []
        for arm in ARM_NAMES:
            key = arm+'/'+name
            source = V1/key
            row = manifest['outputs'][key]
            raw = checked_bytes(source,row['sha256'])
            require(len(raw)==row['size'], 'SIG size mismatch')
            copies.append(raw)
        require(copies[0]==copies[1]==copies[2], 'SIG differs between arms')
        sigs[name], sig_sources[name] = copies[0], [relative(V1/arm/name) for arm in ARM_NAMES]
    background_rows = validation['background_reference_resolution']
    jpg = next(row for row in background_rows if row['raw_reference']=='#data#'+IMAGE)
    image_source = SOURCE_NETWORK.parent/IMAGE
    require(Path(jpg['original_resolved_path']).resolve()==image_source.resolve(), 'Image source path differs from reviewed sidecar')
    require(jpg['original_exists'] is True and jpg['original_size']==95065685, 'Original background contract differs')
    absolute_backgrounds = []
    for row in background_rows:
        if row['raw_reference'].startswith('#data#'):
            continue
        path = Path(row['original_resolved_path'])
        absolute_backgrounds.append({'raw_reference':row['raw_reference'],
            'exists_at_prior_validation':row['original_exists'],'exists_now':path.is_file(),
            'reference_unchanged':True,'introduced_by_flat_package':False})
    # No source or preserved v1 path is opened for writing. Publish manifest last.
    target.mkdir(parents=True, exist_ok=False)
    outputs = {}
    for arm,(source,raw) in networks.items():
        name = arm+'.inpx'
        outputs[name] = {**write_small(target,name,raw), 'source':relative(source),
                         'source_sha256':digest(raw),'network_bytes_unchanged':True}
    for name,raw in sigs.items():
        outputs[name] = {**write_small(target,name,raw), 'sources':sig_sources[name],
                         'source_sha256':digest(raw),'three_v1_copies_exact':True}
    outputs[IMAGE] = copy_image_once(image_source,target)
    for arm in ARM_NAMES:
        for ref in refs[arm]:
            path = (target/ref['shared_filename']).resolve()
            require(path.parent==target and path.is_file(), '#data# destination missing/escaped')
            ref['destination_relative_path'] = ref['shared_filename']
            ref['destination_sha256'] = outputs[ref['shared_filename']]['destination_sha256']
    for row in inputs:
        require(file_digest(ROOT/row['path'])==row['sha256'], 'Pinned small source changed during prepare')
    # Recheck small source artifacts; the JPG was checked by stream hash/stat.
    for source,raw in networks.values():
        require(source.read_bytes()==raw, 'Original v1 network changed during prepare')
    for name,raw in sigs.items():
        require(all((V1/arm/name).read_bytes()==raw for arm in ARM_NAMES), 'Original SIG changed during prepare')
    require({p.name for p in target.iterdir()}==set(outputs), 'Unexpected flat output file set')
    new_manifest = {'schema':'fixed-command-flat-network-assets/v1','inputs':inputs,
        'source_network_sha256':SOURCE_SHA,'preserved_v1_manifest_sha256':V1_SHA,
        'original_native_settings_validation_sha256':VALIDATION_SHA,
        'historical_arm_document_pin_changes':validation['historical_arm_document_pin_changes'],
        'outputs':outputs,'data_references_by_arm':refs,
        'shared_assets':{'sig_count':42,'jpg_count':1,'image_copies_saved_vs_three_folders':2},
        'absolute_background_references':absolute_backgrounds,
        'run_ready':False,'data_reference_filesystem_validation':True,
        'COM_or_model_execution':False,'original_or_v1_writes':False,'source_changes':[],
        'pending':['Variant LoadNet/native route readback and eligible-vehicle coverage',
                   'Fixed-command writer/physical readback gate',
                   'Actual 2D rendering; shared #data# paths are filesystem-validated only'],
        'host_dependencies':'Unchanged #exe#/#3dmodels#/VISSIG DLL and absolute PNG references; this is not a standalone VISSIM installation.'}
    raw = (json.dumps(new_manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    write_small(target,'manifest.json',raw)
    print(json.dumps({'output':str(target),'files':len(outputs)+1,'manifest_sha256':digest(raw),
                      'image_sha256':outputs[IMAGE]['source_sha256'],'run_ready':False,'source_changes':[]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    prepare(output_path(args.output))


if __name__ == '__main__':
    main()
