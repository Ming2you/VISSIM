"""Snapshot physical identity, with an explicit recording-only INPX proof.

Without ``network_recording`` the legacy fingerprint contract is unchanged.
With it, files.network remains the *loaded* file's truthful SHA; only this
function returns the validated physical source SHA for calibration contracts.
"""
from collections import OrderedDict
import hashlib
import json
from pathlib import Path
import re
from xml.parsers import expat

RECORDING_SCHEMA = 'native-signal-recording-network/v1'
_PROOF_CACHE = OrderedDict()
_CACHE_LIMIT = 8


def _groups(groups):
    if not isinstance(groups, dict) or not groups:
        raise ValueError('Recording groups must be a nonempty controller map')
    result = {}
    for key, values in groups.items():
        if type(key) is int:
            sc = key
        elif type(key) is str and re.fullmatch(r'[1-9][0-9]*', key):
            sc = int(key)
        else:
            raise ValueError('Invalid recording controller number')
        if sc <= 0 or sc in result or type(values) not in (list, tuple) or not values:
            raise ValueError('Duplicate/empty recording controller')
        if any(type(v) is not int or v <= 0 for v in values) or len(set(values)) != len(values):
            raise ValueError('Invalid/duplicate recording signal group')
        result[sc] = tuple(sorted(values))
    return tuple(sorted(result.items()))


def _layout(data):
    """Obtain actual XML byte spans; comments/quoted text are never elements."""
    if type(data) is not bytes:
        raise ValueError('Network input must be immutable bytes')
    parser = expat.ParserCreate()
    stack = []; controllers = {}; evaluations = []; recordings = []
    def start(tag, attrs):
        pos = parser.CurrentByteIndex
        # The XML parser has already recognized a start tag. Respect quoted >.
        quote = None; end = pos
        while end < len(data):
            char = data[end]
            if quote is not None:
                if char == quote: quote = None
            elif char in (34, 39): quote = char
            elif char == 62: break
            end += 1
        node = {'tag': tag, 'attrs': attrs, 'start': pos, 'open_end': end+1,
                'self_closing': data[pos:end].rstrip().endswith(b'/')}
        path = tuple(n['tag'] for n in stack) + (tag,)
        if not stack and tag != 'network':
            raise ValueError('Expected a native network root')
        if path == ('network', 'signalControllers', 'signalController'):
            try: sc = int(attrs['no'])
            except (KeyError, ValueError): raise ValueError('Invalid native controller identity')
            if sc <= 0 or sc in controllers: raise ValueError('Duplicate native controller identity')
            node['groups'] = set(); node['recordings'] = []; controllers[sc] = node
        elif path == ('network', 'signalControllers', 'signalController', 'sgs', 'signalGroup'):
            try: sg = int(attrs['no'])
            except (KeyError, ValueError): raise ValueError('Invalid native signal group identity')
            owned = stack[-2]['groups']
            if sg <= 0 or sg in owned: raise ValueError('Duplicate native signal group identity')
            owned.add(sg)
        elif path == ('network', 'signalControllers', 'signalController', 'scDetRecConf'):
            stack[-1]['recordings'].append(node)
        elif path == ('network', 'evaluation'):
            evaluations.append(node)
        elif path == ('network', 'evaluation', 'scDetRec'):
            recordings.append(node)
        stack.append(node)
    def end(tag):
        node = stack.pop()
        node['end'] = (node['open_end'] if node['self_closing'] else
                       data.index(b'>', parser.CurrentByteIndex)+1)
    def reject_doctype(*args):
        raise ValueError('Network recording proof does not support DTD/entities')
    parser.StartElementHandler = start; parser.EndElementHandler = end
    parser.StartDoctypeDeclHandler = reject_doctype
    try: parser.Parse(data, True)
    except expat.ExpatError as exc: raise ValueError('Malformed network XML') from exc
    if len(evaluations) != 1 or len(recordings) != 1:
        raise ValueError('Expected exactly one evaluation/scDetRec')
    return controllers, recordings[0]


def _recording_edits(source_bytes, groups):
    controllers, evaluation = _layout(source_bytes)
    edits = []
    for sc, signal_groups in _groups(groups):
        if sc not in controllers or not set(signal_groups) <= controllers[sc]['groups']:
            raise ValueError('Recording group is absent from the native network')
        node = controllers[sc]
        if node['self_closing'] or len(node['recordings']) > 1:
            raise ValueError('Unsupported/duplicate native recording configuration')
        rows = ['<scDetRecConf>',
            '\t\t\t\t<signalOutputConfigurationElement configName="SIM_SEK" detPort="0" title="" varNo="0" wttFilename="vissim" />',
            '\t\t\t\t<signalOutputConfigurationElement configName="UML_SEK" detPort="0" title="" varNo="0" wttFilename="vissim" />']
        rows.extend(f'\t\t\t\t<signalOutputConfigurationElement configName="SG_BILD" detPort="0" sg="{sc} {sg}" title="" varNo="{sg}" wttFilename="vissim" />' for sg in signal_groups)
        rows.append('\t\t\t\t</scDetRecConf>')
        block = '\n'.join(rows).encode('ascii')
        if node['recordings']:
            previous = node['recordings'][0]
            edits.append((previous['start'], previous['end'], block))
        else:
            edits.append((node['open_end'], node['open_end'], b'\n\t\t\t'+block))
    if evaluation['attrs'].get('writeFile') not in ('false', 'true'):
        raise ValueError('Expected a Boolean native scDetRec.writeFile')
    start, end = evaluation['start'], evaluation['open_end']
    opening = source_bytes[start:end]
    # Match complete attributes so a quoted title containing writeFile cannot
    # redirect the allowed edit to a different attribute.
    attributes = list(re.finditer(rb"([^\s=<>/]+)\s*=\s*([\"'])(.*?)\2", opening, re.S))
    matches = [m for m in attributes if m.group(1) == b'writeFile']
    if len(matches) != 1 or matches[0].group(3) not in (b'true', b'false'):
        raise ValueError('Unsupported recording writeFile encoding')
    match = matches[0]
    edits.append((start+match.start(3), start+match.end(3), b'true'))
    return sorted(edits)


def prepare_recording_bytes(source_bytes, groups):
    """Return the native_all_sg_300_v1 SG_BILD format without rewriting XML.

Only selected scDetRecConf children are added/replaced and evaluation/scDetRec
writeFile is set to true. Existing non-recording whitespace/bytes stay exact.
The caller owns output paths, native assets, run identity and file creation.
"""
    edits = _recording_edits(source_bytes, groups)
    result = source_bytes
    for start, end, replacement in reversed(edits):
        result = result[:start]+replacement+result[end:]
    return result


def validate_recording_bytes(source_bytes, recorded_bytes, groups):
    """Require exact reproducible recording bytes, not just XML similarity.

Regeneration pins every byte outside the permitted replacement spans to the
source, including geometry, routes, demand, attributes and whitespace. The
original source spans retained by the proof make the transformation reversible.
"""
    if type(recorded_bytes) is not bytes or prepare_recording_bytes(source_bytes, groups) != recorded_bytes:
        raise ValueError('Network differs beyond the exact recording-only transformation')


def _pin(pin):
    if not isinstance(pin, dict) or not isinstance(pin.get('path'), str):
        raise ValueError('Recording network pin lacks a path')
    path = Path(pin['path'])
    value = pin.get('sha256')
    if not path.is_absolute() or not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Recording network pin requires absolute path and SHA256')
    return path.resolve(strict=True), value


def _stat(path):
    value = path.stat()
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def validate_recording_proof(proof):
    """Validate both on-disk SHAs/byte whitelist; return PHYSICAL source SHA.

A bounded cache holds successful immutable proof keys (pins, groups, file stat
identities), not caller dictionaries. Every call stats both files; a changed
identity triggers full revalidation. This assumes frozen run inputs and a
filesystem whose stat identity changes on writes; it is not an adversarial
same-stat filesystem tamper detector. Startup and new processes validate afresh.
"""
    if not isinstance(proof, dict) or proof.get('schema') != RECORDING_SCHEMA:
        raise ValueError('Unsupported network recording proof schema')
    groups = _groups(proof.get('groups'))
    source, source_sha = _pin(proof.get('source_network'))
    recorded, recorded_sha = _pin(proof.get('recorded_network'))
    if source == recorded: raise ValueError('Recording output must be separate from its physical source')
    before = (_stat(source), _stat(recorded))
    key = (str(source), source_sha, str(recorded), recorded_sha, groups, before)
    if key in _PROOF_CACHE:
        _PROOF_CACHE.move_to_end(key)
        return source_sha
    source_bytes, recorded_bytes = source.read_bytes(), recorded.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != source_sha or hashlib.sha256(recorded_bytes).hexdigest() != recorded_sha:
        raise ValueError('Network recording proof file SHA differs')
    validate_recording_bytes(source_bytes, recorded_bytes, dict(groups))
    if before != (_stat(source), _stat(recorded)):
        raise ValueError('Network file changed while validating recording proof')
    _PROOF_CACHE[key] = True
    while len(_PROOF_CACHE) > _CACHE_LIMIT: _PROOF_CACHE.popitem(last=False)
    return source_sha


def _snapshot_provenance(state_json):
    provenance = state_json.get('run_provenance') or {}
    if provenance.get('manifest_path'):
        manifest = json.loads(Path(provenance['manifest_path']).read_text(encoding='utf-8-sig'))
        if not provenance.get('run_id') or manifest.get('run_id') != provenance['run_id']:
            raise ValueError('Snapshot and provenance manifest run IDs differ')
        provenance = manifest
    return provenance


def _physical_recording_sha256(state_json, provenance):
    proof = provenance['network_recording']
    if not isinstance(proof, dict) or not provenance.get('run_id'):
        raise ValueError('Recording snapshot lacks run identity')
    if 'run_id' in proof and proof['run_id'] != provenance['run_id']:
        raise ValueError('Recording proof and snapshot run IDs differ')
    loaded = (provenance.get('files') or {}).get('network')
    recorded = proof.get('recorded_network')
    if _pin(loaded) != _pin(recorded):
        raise ValueError('Loaded network differs from recording proof')
    if 'network_path' in state_json and Path(state_json['network_path']).resolve(strict=True) != _pin(recorded)[0]:
        raise ValueError('Snapshot network path differs from loaded recording network')
    return validate_recording_proof(proof)


def snapshot_network_sha256(state_json):
    """Return legacy loaded SHA, or proven recording-only PHYSICAL source SHA."""
    provenance = _snapshot_provenance(state_json)
    if 'network_recording' in provenance:
        return _physical_recording_sha256(state_json, provenance)
    value = ((provenance.get('files') or {}).get('network') or {}).get('sha256')
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError('Snapshot lacks a valid network fingerprint')
    return value


def snapshot_physical_file_sha256(state_json):
    """Explicit recording-enabled direct-file consumer; no proof means failure.

Callers retain their original direct-file guard when the config opt-in is OFF.
Actual geometry must still be read from state_json.network_path.
"""
    provenance = _snapshot_provenance(state_json)
    if 'network_recording' not in provenance or 'network_path' not in state_json:
        raise ValueError('Recording-enabled head guard requires a loaded-network proof')
    return _physical_recording_sha256(state_json, provenance)
