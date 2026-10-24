"""Three bounded native diagnostics: distribution mean, spread and their sum."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.fast_fixed_profile import prepare
from evaluation.controllers.desired_speed_transport import SpeedDistribution
import xml.etree.ElementTree as ET
import copy
import hashlib

HERE=Path(__file__).resolve().parent;H=HERE.parent


def normalized(node):return node.tag,dict(node.attrib),(node.text or '').strip(),[normalized(c) for c in node]


def main():
    out=HERE/'dispersion_native_v1';out.mkdir(exist_ok=False)
    source=H/'dsd_response_20260920/native_v2/prepared/network/baseline.inpx'
    content=source.read_bytes();root=ET.fromstring(content)
    distributions={int(x.get('no')):x for x in root.findall('./desSpeedDistributions/desSpeedDistribution')}
    def distribution(n):return SpeedDistribution(tuple((float(p.get('fx')),float(p.get('x')))
        for p in distributions[n].findall('./speedDistrDatPts/speedDistributionDataPoint')))
    moments={k:distribution(k).moments() for k in [100,120]}
    mean0,mean1=[moments[k]['mean_kmh'] for k in [120,100]]
    scale=moments[100]['sd_kmh']/moments[120]['sd_kmh']
    ids=[n for n in range(100,120) if n not in distributions][:3]
    assert len(ids)==3
    cases=[('mean_only',mean1,1.),('spread_only',mean0,scale),('affine_both',mean1,scale)]
    evidence={}
    for (name,mean,mult),number in zip(cases,ids):
        folder=out/name;folder.mkdir()
        candidate=ET.fromstring(content);container=candidate.find('desSpeedDistributions')
        new=copy.deepcopy(distributions[120]);new.set('no',str(number));new.set('name','DIAGNOSTIC_'+name)
        for p in new.findall('./speedDistrDatPts/speedDistributionDataPoint'):
            p.set('x',format(mean+mult*(float(p.get('x'))-mean0),'.12g'))
        container.append(new)
        container.remove(new);assert normalized(candidate)==normalized(root);container.append(new)
        target=folder/'source';target.mkdir();network=target/'baseline.inpx'
        network.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(candidate,encoding='utf-8'))
        for asset in set(v[6:] for node in root.iter() for v in node.attrib.values() if v.startswith('#data#')):
            assert Path(asset).name==asset
            (target/asset).write_bytes((source.parent/asset).read_bytes())
        profile=e.load(H/'dsd_response_20260920/native_v2/profile.json')
        for command in profile['vsl_commands']:
            assert command['speed_id']==100 and 51<=command['dsd_no']<=58
            command['speed_id']=number
        profile['network_sha256']=hashlib.sha256(network.read_bytes()).hexdigest()
        e.save(folder/'profile.json',profile);prepare(network,folder/'profile.json',folder/'prepared')
        actual=SpeedDistribution(tuple((float(p.get('fx')),float(p.get('x')))
            for p in new.findall('./speedDistrDatPts/speedDistributionDataPoint'))).moments()
        assert abs(actual['mean_kmh']-mean)<1e-7
        assert abs(actual['sd_kmh']-mult*moments[120]['sd_kmh'])<1e-7
        evidence[name]={'distribution_id':number,'moments':actual,'points':[dict(p.attrib) for p in new.findall('./speedDistrDatPts/speedDistributionDataPoint')],
            'network_sha256':profile['network_sha256']}
    e.save(out/'protocol.json',{'purpose':'Causal diagnostic of desired-speed mean/spread, NOT an operational MPC candidate set',
        'seed':23,'start_s':2400,'terminal_s':3000,'evaluation_window_s':[2400,2850],
        'source':str(source.relative_to(e.ROOT)),'source_sha256':hashlib.sha256(content).hexdigest(),
        'unchanged':'All original XML physical settings / original distributions / demand / routing / signals / DSD positions; add one previously unreferenced distribution per network',
        'command_timing':'Same51..58 commands at2400/2550/2700/2850, different distribution ID only',
        'required_checks':['Pre2400 original9 FZP fields exact vs known VSL reference','Native LDP and VSL application readback','Desired-speed transformation at DSD crossings'],
        'baseline_distribution_moments':moments,'cases':evidence,
        'limits':'Affine_both matches100 mean/SD but keeps120 standardized quantile shape. Compare to actual100 separately. Single seed; no significance or general capacity claim.'})
    print(evidence,flush=True)


def seed33():
    source=HERE/'dispersion_native_v1/spread_only'
    folder=HERE/'dispersion_seed33_v1/spread_only';folder.mkdir(parents=True,exist_ok=False)
    target=folder/'source';target.mkdir()
    root=ET.parse(source/'source/baseline.inpx').getroot()
    assert root.find('simulation').get('randSeed')=='23'
    root.find('simulation').set('randSeed','33')
    network=target/'baseline.inpx'
    network.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding='utf-8'))
    for asset in set(v[6:] for node in root.iter() for v in node.attrib.values() if v.startswith('#data#')):
        assert Path(asset).name==asset
        (target/asset).write_bytes((source/'source'/asset).read_bytes())
    profile=e.load(source/'profile.json');profile['seed']=33
    profile['network_sha256']=hashlib.sha256(network.read_bytes()).hexdigest()
    e.save(folder/'profile.json',profile);prepare(network,folder/'profile.json',folder/'prepared')
    e.save(folder.parent/'protocol.json',{'seed':33,'control_start':2400,'terminal':3000,'arm':'spread_only',
        'source_case':str(source),'only_additional_edit':'randSeed23->33; same distribution102, DSD51..58, commands, geometry/demand/signals',
        'purpose':'Second-seed check of newly tested mean-preserving dispersion intervention; previously inspected seed, not a new calibration holdout',
        'reference_bank':'state_response_20260919/native_s33_v1','selection':'Chosen after seed23; no parameter adjustment'})


if __name__=='__main__':
    if sys.argv[1:]==['--seed33']:seed33()
    elif not sys.argv[1:]:main()
    else:raise SystemExit('Use no arguments for seed23, or --seed33 for replication')
