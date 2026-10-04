"""Prepare reviewable 10484 conflict/cooperation variants; never start VISSIM."""
from pathlib import Path
import copy
import csv
import hashlib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
OLD = ROOT.parent/'control-full-review'
STUDY = HERE.parents[1]
PRIOR = Path('D:/VISSIM_runs/20260924_release2670_s47')
sys.path.insert(0, str(OLD/'diagnostics'))
from fast_fixed_profile import compile_profile, prepare


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    source = OLD/'diagnostics/metanet_net_gain_goal_20260924/release2670_seed47/source_s47.inpx'
    raw = source.read_bytes()
    assert sha(source) == 'ff1ffa0aa5b9022795f5e2b7338b2426030ad9f67d430a0e7a9b329cb0c14df4'
    selected = STUDY/'selected/network/native_seed29.inpx'
    assert re.sub(rb'(<simulation\b[^>]*\brandSeed=")47(")', rb'\g<1>29\2', raw) == selected.read_bytes()
    target = HERE/'source'; target.mkdir(exist_ok=False)
    root = ET.fromstring(raw)
    assets = sorted({v[6:] for n in root.iter() for v in n.attrib.values() if v.startswith('#data#')})
    for name in assets:
        shutil.copy2(PRIOR/'source'/name, target/name)
        assert sha(target/name) == sha(PRIOR/'source'/name)

    ca = re.search(rb'<conflictArea\b[^>]*\bno="2867"[^>]*/>', raw).group()
    assert b'link1="24" link2="10484"' in ca and b'status="PASSIVE"' in ca
    priority = ca.replace(b'status="PASSIVE"', b'status="ONEYIELDSTWO"')
    behavior = re.search(rb'<drivingBehavior\b[^>]*\bno="3"[^>]*(?:/>|>.*?</drivingBehavior>)', raw, re.S).group()
    assert b'coopLnChg="false"' in behavior and b'advMerg="true"' in behavior
    new_behavior = behavior.replace(b' no="3"', b' no="6"').replace(b'coopLnChg="false"', b'coopLnChg="true"')
    assert new_behavior != behavior
    link_behavior = re.search(rb'<linkBehaviorType\b[^>]*\bno="3"[^>]*>.*?</linkBehaviorType>', raw, re.S).group()
    new_link_behavior = link_behavior.replace(b' no="3"', b' no="6"').replace(b'drivBehavDef="3"', b'drivBehavDef="6"').replace(b'drivBehav="3"', b'drivBehav="6"')
    link = re.search(rb'<link\b[^>]*\bno="24"[^>]*>', raw).group()
    assert b'linkBehavType="3"' in link
    cooperative_link = link.replace(b'linkBehavType="3"', b'linkBehavType="6"')
    profiles = {name:json.loads((PRIOR/(name+'.json')).read_bytes()) for name in ('hold','release_10484')}
    differences = [(x,y) for x,y in zip(profiles['hold']['meter_commands'],profiles['release_10484']['meter_commands']) if x != y]
    assert len(differences) == 4
    assert all(x['sc_no'] == y['sc_no'] == 9108 and x['time_s'] == y['time_s'] >= 2700 for x,y in differences)
    assert profiles['hold']['vsl_commands'] == profiles['release_10484']['vsl_commands']
    audits = {}; plans = []
    for name, use_priority, use_cooperation in (('baseline',False,False),('priority',True,False),('cooperation',False,True),('both',True,True)):
        data = raw
        if use_priority: data = data.replace(ca, priority, 1)
        if use_cooperation:
            data = data.replace(behavior, behavior+b'\n\t\t'+new_behavior, 1)
            data = data.replace(link_behavior, link_behavior+b'\n\t\t'+new_link_behavior, 1)
            data = data.replace(link, cooperative_link, 1)
        restored = data
        if use_cooperation:
            restored = restored.replace(b'\n\t\t'+new_behavior,b'',1).replace(b'\n\t\t'+new_link_behavior,b'',1).replace(cooperative_link,link,1)
        if use_priority: restored = restored.replace(priority,ca,1)
        assert restored == raw
        parsed = ET.fromstring(data)
        assert parsed.find('./conflictAreas/conflictArea[@no="2867"]').get('status') == ('ONEYIELDSTWO' if use_priority else 'PASSIVE')
        assert parsed.find('./links/link[@no="24"]').get('linkBehavType') == ('6' if use_cooperation else '3')
        assert all(ET.tostring(parsed.find('./'+tag)) == ET.tostring(root.find('./'+tag)) for tag in ('vehicleInputs','vehicleRoutingDecisionsStatic','desSpeedDecisions','signalControllers','simulation'))
        network = target/('merge10484_'+name+'_s47.inpx'); network.write_bytes(data)
        audits[name] = dict(network=str(network),sha256=sha(network),priority=use_priority,cooperative_lane_change=use_cooperation,restoration_to_original_exact=True)
        event_tables = []
        for arm, original in profiles.items():
            profile = copy.deepcopy(original); profile['network_sha256'] = sha(network)
            profile_path = HERE/(name+'_'+arm+'.json'); save(profile_path,profile)
            events, initial, proof = compile_profile(network,profile)
            event_tables.append(events)
            with (HERE/(name+'_'+arm+'_events.csv')).open('w',newline='',encoding='ascii') as stream:
                writer=csv.writer(stream); writer.writerow(['time_s','kind','no','veh_class','value']); writer.writerows(events)
            save(HERE/(name+'_'+arm+'_compile.json'),proof)
            if name == 'priority':
                prepared = HERE/('prepared_'+name+'_'+arm)
                meta = prepare(network,profile_path,prepared)
                meta['concurrent_identity_network_stem'] = network.stem
                save(prepared/'prepared.json',meta)
                plans.append(dict(arm=arm,prepared=str(prepared),output='D:/VISSIM_runs/20260928_merge10484_priority_s47/'+arm+'/run',concurrent=False))
        assert [r for r in event_tables[0] if r[0]<2700] == [r for r in event_tables[1] if r[0]<2700]
    save(HERE/'prepared_review.json',dict(stage='prepared_not_launched_requires_scope_confirmation',source=dict(path=str(source),sha256=sha(source)),variants=audits,
        seed=47,terminal_sec=3300,evaluation_window=[2670.1,3120.1],intervention_sec=2700,
        rm_pair='Only10484: hold g2 versus legal4/6/8/10 from2700/2850/3000/3150; other7meters andallVSL fixed identically.',
        common_initial_scope='Same network within each hold/release pair only. Priority/cooperation are active from t0, so different network variants are NOT a common2670.1 initial state.',
        baseline_reuse=str(PRIOR),stage1_new_runs=2,stage1_plans=plans,
        cooperation_scope='New behavior6 clones3 with only coopLnChg enabled, used only by entire mainline link24 (~3.346km). Other links and original behavior3 unchanged. This is not an exact short-cell-only intervention.',
        native_load_validation_pending=True,new_native_runs=0,stop_preserved=True,push=False,
        source_pins={str(p):sha(p) for p in (Path(__file__),OLD/'diagnostics/fast_fixed_profile.py',OLD/'diagnostics/fast_nc_prepare.py',OLD/'diagnostics/fast_nc_run.ps1',OLD/'diagnostics/fast_nc_runner.vbs')},
        notes=['Automatic conflict typing retained; inactive manual CROSSING field not interpreted as effective type.','Verify native loaded2867 status/link identity/type before simulation; static XML proof is not COM readback.','Do not activate all geometrical overlap areas.','Prepared2 stage1 jobs are sequential because they share one network identity; preserve user open VISSIM.']))
    print('Four source variants compiled; two priority-only jobs prepared; no VISSIM started.')


if __name__ == '__main__':
    main()
