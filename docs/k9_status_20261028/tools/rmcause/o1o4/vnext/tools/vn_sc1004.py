# VERIFY_NEXT: model service of SC1004 *_to_W movements (feed of link 68) for one decision (read-only)
import json, sys
p, ti = sys.argv[1], int(sys.argv[2])
d = json.load(open(p, encoding='utf-8'))
td = d['metadata']['joint_leader_selection']['tangent_derivatives'][ti]['surrogate_prediction']
srv = td['quantities']['served_by_movement_veh']
fc = td['control_area']['flow_counts']
for mv in sorted(k for k in srv if k.startswith('SC1004') and k.endswith('_to_W')):
    print(mv, 'served_veh_450s %.2f -> %.1f veh/h' % (srv[mv], srv[mv] / 0.125), 'arrival', fc.get('arrival:' + mv), 'movement', fc.get('movement:' + mv))
print('greens SC1004', {k: v for k, v in d['green_times'].items() if k.startswith('SC1004')})
