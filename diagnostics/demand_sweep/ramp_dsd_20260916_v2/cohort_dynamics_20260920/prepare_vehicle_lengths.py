"""Native observation repeats: append fields, leave traffic unchanged."""
from pathlib import Path
import sys
import hashlib
import re
import argparse
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.fast_fixed_profile import prepare

HERE=Path(__file__).resolve().parent


def prepare_body_coordinates(resolution):
    """Paired observation / integration-resolution diagnostic, no control writes."""
    import openpyxl
    base=HERE/'route_state_native_v1/none_s23'
    source=base/'source/baseline.inpx';original=source.read_bytes();root=ET.fromstring(original)
    out=HERE/'body_geometry_native_v1'/f'none_s23_res{resolution}'
    out.mkdir(parents=True,exist_ok=False)
    fields=[('COORDFRONTX',4),('COORDFRONTY',4),('COORDREARX',4),('COORDREARY',4),('ACCELERATION',4)]
    doc=Path('C:/Program Files/PTV Vision/PTV Vissim 2020/Doc/Eng/attribute.xlsx')
    book=openpyxl.load_workbook(doc,read_only=True,data_only=True);rows=iter(book['Attributes'].values);columns=next(rows)
    values={d['AttributeID'].upper():d for row in rows if (d:=dict(zip(columns,row)))['Object']=='Vehicle'}
    documentation={name:{key:values[name][key] for key in ('AttributeID','ValueType','Description(ENG)')} for name,_ in fields}
    book.close()
    extra=''.join(f'<attributeSelection attributeID="{name}" decimals="{decimals}" format="DEFAULT" showUnits="false"/>\n' for name,decimals in fields).encode()
    changed,n=re.subn(rb'(<vehRec\b[^>]*>\s*<attributes>)(.*?)(</attributes>)',lambda m:m[1]+m[2]+extra+m[3],original,flags=re.S)
    assert n==1 and root.find('simulation').get('simRes')=='1'
    changed,n=re.subn(rb'(<simulation\b[^>]*\bsimRes=")1(")',lambda m:m[1]+str(resolution).encode()+m[2],changed)
    assert n==1
    edited=ET.fromstring(changed);attrs=edited.find('./evaluation/vehRec/attributes')
    assert len(attrs)==25 and [v.get('attributeID') for v in list(attrs)[-5:]]==[f[0] for f in fields]
    for node in list(attrs)[-5:]:attrs.remove(node)
    edited.find('simulation').set('simRes','1')
    def norm(node):return node.tag,dict(node.attrib),(node.text or '').strip(),[norm(c) for c in node]
    assert norm(edited)==norm(root)
    target=out/'source';target.mkdir();network=target/'baseline.inpx';network.write_bytes(changed)
    for name in set(v[6:] for node in root.iter() for v in node.attrib.values() if v.startswith('#data#')):
        assert Path(name).name==name
        (target/name).write_bytes((source.parent/name).read_bytes())
    profile=e.load(base/'profile.json')
    assert profile['seed']==23 and not profile['vsl_commands'] and not profile['meter_commands'] and profile['terminal_sec']==3000
    profile.update(network_sha256=hashlib.sha256(changed).hexdigest(),native_resolution_probe=resolution)
    e.save(out/'profile.json',profile);prepare(network,out/'profile.json',out/'prepared')
    e.save(out/'protocol.json',dict(source=str(source.relative_to(e.ROOT)),source_sha256=hashlib.sha256(original).hexdigest(),
        saved_resolution=1,diagnostic_resolution=resolution,end_s=3000,seed=23,
        allowed_xml_changes=['five vehicle recording attributes','simulation.simRes'],other_xml_exact=True,
        expected_original20_fzp_exact=resolution==1,not_equivalent_traffic=resolution!=1,
        new_control_commands=0,live_vehicle_queries=0,recording_interval_s=1,initial_no_progress_watchdog_s=300,
        fields=fields,attribute_documentation=documentation,attribute_documentation_sha256=hashlib.sha256(doc.read_bytes()).hexdigest(),
        purpose='Resolve projected overlaps using actual front/rear coordinates and separately test coarse numerical resolution; no benefit qualification'))
    print(out)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--route-state',action='store_true')
    ap.add_argument('--body-resolution',type=int,choices=(1,10),default=None)
    ap.add_argument('--case',choices=['none_s23','vsl_s23','rm_ramp_s23'],default='none_s23');args=ap.parse_args()
    if args.body_resolution is not None:
        if args.route_state or args.case!='none_s23':ap.error('Body-resolution probe is native NC only')
        prepare_body_coordinates(args.body_resolution);return
    if args.case!='none_s23' and not args.route_state:ap.error('VSL repetition requires route-state mode')
    if args.case=='none_s23':
        source=HERE/'native_v1/none_s23/source/baseline.inpx'
        profile_file=HERE/'native_v1/none_s23/profile.json';reference=HERE/'native_v1/none_s23/run'
    elif args.case=='rm_ramp_s23':
        reference=HERE.parent/'response_late_s23_v1/run_rm_ramp'
        source=Path(e.load(reference/'run.json')['network'])
        profile_file=reference.parent/'rm_ramp.json'
    else:
        reference=HERE.parent/'dsd_response_20260920/native_v2/run_retry1'
        source=Path(e.load(reference/'run.json')['network'])
        profile_file=reference.parent/'profile.json'
    out=HERE/'route_state_native_v1'/args.case if args.route_state else HERE/'vehicle_lengths_native_v1'
    out.mkdir(parents=True,exist_ok=False)
    original=source.read_bytes();root=ET.fromstring(original)
    attrs=root.find('./evaluation/vehRec/attributes');original_columns=len(attrs)
    assert original_columns==(9 if args.case=='rm_ramp_s23' else 10)
    fields=[('LENGTH',3),('VEHTYPE\\NO',0)]
    documentation=None
    if args.route_state:
        fields=[('LENGTH',3),('ROUTDECNO',0),('ROUTENO',0),('ROUTDECTYPE',0),('NEXTLINK\\NO',0),
            ('DESTLANE',0),('LNCHG',0),('INTERACTSTATE',0),('INTERACTTARGTYPE',0),('INTERACTTARGNO',0)]
        if original_columns==9:fields.insert(0,('DESSPEED',2))
        # Exact installed2020 attribute IDs; DestLane is a CURRENT lane-change
        # destination, not the full route's required connector lane.
        import openpyxl
        doc=Path('C:/Program Files/PTV Vision/PTV Vissim 2020/Doc/Eng/attribute.xlsx')
        book=openpyxl.load_workbook(doc,read_only=True,data_only=True);it=iter(book['Attributes'].values);columns=next(it)
        values={d['AttributeID'].upper():d for row in it if (d:=dict(zip(columns,row)))['Object']=='Vehicle'}
        documentation={name:{key:values[name.split('\\')[0]][key] for key in ('AttributeID','ValueType','Description(ENG)')} for name,_ in fields}
        book.close();e.save(out/'attribute_documentation.json',dict(path=str(doc),sha256=hashlib.sha256(doc.read_bytes()).hexdigest(),fields=documentation))
    extra=''.join(f'<attributeSelection attributeID="{name}" decimals="{decimals}" format="DEFAULT" showUnits="false"/>\n' for name,decimals in fields).encode('ascii')
    changed,n=re.subn(rb'(<vehRec\b[^>]*>\s*<attributes>)(.*?)(</attributes>)',
        lambda m:m[1]+m[2]+extra+m[3],original,flags=re.S);assert n==1
    edited=ET.fromstring(changed);selected=edited.find('./evaluation/vehRec/attributes')
    assert [n.get('attributeID') for n in list(selected)[-len(fields):]]==[name for name,_ in fields]
    for node in list(selected)[-len(fields):]:selected.remove(node)
    def norm(node):return node.tag,dict(node.attrib),(node.text or '').strip(),[norm(c) for c in node]
    assert norm(edited)==norm(root)
    target=out/'source';target.mkdir();network=target/'baseline.inpx';network.write_bytes(changed)
    for name in set(v[6:] for node in root.iter() for v in node.attrib.values() if v.startswith('#data#')):
        assert Path(name).name==name
        (target/name).write_bytes((source.parent/name).read_bytes())
    profile=e.load(profile_file)
    assert profile['seed']==23
    assert bool(profile['meter_commands'])==(args.case=='rm_ramp_s23')
    assert bool(profile['vsl_commands'])==(args.case=='vsl_s23')
    removed_commands={key:[r for r in profile[key] if r['time_s']>=3000] for key in ('meter_commands','vsl_commands')}
    for key in removed_commands:profile[key]=[r for r in profile[key] if r['time_s']<3000]
    profile.update(terminal_sec=3000,network_sha256=hashlib.sha256(changed).hexdigest())
    e.save(out/'profile.json',profile);prepare(network,out/'profile.json',out/'prepared')
    e.save(out/'protocol.json',{'seed':23,'end_s':3000,'source':str(source.relative_to(e.ROOT)),
        'source_sha256':hashlib.sha256(original).hexdigest(),'new_source_sha256':hashlib.sha256(changed).hexdigest(),
        'physical_xml_equal_after_removing_added_attributes':True,'fields_added':[name for name,_ in fields],
        'commands':profile['vsl_commands'],'meter_commands':profile['meter_commands'],
        'omitted_commands_at_or_after_terminal':removed_commands,'original_fzp_columns':original_columns,'reference_run':str(reference.relative_to(e.ROOT)),
        'required_gate':f'All original{original_columns} FZP fields exactly equal through3000, native signal validation, nonempty added attributes',
        'purpose':('Observe current route/next-link/lane-access state without future route labels' if args.route_state else 'Distinguish heterogeneous vehicle occupancy from empty storage')+'; observation repeat, not independent benefit validation',
        'startup_watchdog_s':300,'live_vehicle_queries':0,
        'attribute_documentation':'https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/9_SimulationundTest/Simulation_Fz_im_Netz_anz.htm'})
    print(out)


if __name__=='__main__':main()
