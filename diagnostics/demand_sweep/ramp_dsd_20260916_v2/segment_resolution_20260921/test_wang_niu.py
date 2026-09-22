"""Wang--Niu Eq4 branch closure, preserving the conserved allocator."""
import unittest
from test_hadiuzzaman import ConservedReceiving
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups,hadi_receiving_vph
import canonical_harness as ch


class Branch(unittest.TestCase):
    def test_zero_drop_continuous_and_positive_drop_unmasked(self):
        q,jam,crit=2200.,180.,2200./120.
        wave=q/(jam-crit)
        f=lambda rho,theta:hadi_receiving_vph(rho,jam,crit,q,wave,theta,capacity_critical=True)
        self.assertEqual(f(crit,0),q)
        self.assertAlmostEqual(f(crit+1e-8,0),q,places=5)
        self.assertAlmostEqual(f(80,.15),.85*f(80,0))
        self.assertEqual(f(jam,.15),0)
        self.assertEqual(f(crit-1,.15),q)

    def test_no_drop_closure_equals_matching_fixed_wave(self):
        for rho in (0,10,27,28,60,179,180,190):
            wave=2200/(180-27)
            self.assertEqual(hadi_receiving_vph(rho,180,27,2200,wave,0),
                hadi_receiving_vph(rho,180,27,2200,wave,0,capacity_critical=True))

    def test_literal_paper_sending_is_not_an_upstream_stock_limit(self):
        # Eq3 as printed adds downstream net ramp flow to v*rho. It therefore
        # cannot replace our stock-limited upstream sending at an empty cell.
        rho,v,r,s,lanes=0,100,600,0,3
        printed_sending=v*rho+(r-s)/lanes
        self.assertEqual(printed_sending,200)
        self.assertGreater(printed_sending,0)


class Hook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ConservedReceiving.setUpClass()

    def test_group_room_uses_new_branch_and_physical_storage(self):
        spec,state,cfg=ConservedReceiving().fixture()
        cfg.network.freeway_hadiuzzaman={'FW_E':dict(ctm=True,relaxation='fd_cap',congested_branch='capacity_critical',
            cells=[dict(capacity_vphpl=1700,wave_kmh=11.5,rho_critical=40,theta=.15) for _ in spec['widths']])}
        p=PhysicalLaneGroups(spec,state,cfg,ch.accounting)
        length=p.lengths[0];widths=p.widths[0];rho=80
        room=p._hadi_room(0,[rho*length*w for w in widths],length,cfg)
        q=1445*(cfg.network.rho_max-rho)/(cfg.network.rho_max-40)
        for r,w in zip(room,widths):self.assertAlmostEqual(r,min((cfg.network.rho_max-rho)*length*w,p.dt*w*q))
        self.assertEqual(p._hadi_room(0,[cfg.network.rho_max*length*w for w in widths],length,cfg),[0.]*len(widths))


if __name__=='__main__':unittest.main()
