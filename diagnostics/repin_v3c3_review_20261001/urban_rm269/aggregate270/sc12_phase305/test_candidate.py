import copy,json,unittest
from pathlib import Path
from types import SimpleNamespace
import candidate as c
from evaluation.controllers import local_signal_service as service
HERE=Path(__file__).resolve().parent
class Checks(unittest.TestCase):
    def setUp(self):
        self.doc=json.loads((HERE/"past_shared_prefix_support.json").read_bytes())
        path=HERE.parent.parent/"sc12w_service/forecast2400_checked/network.json"
        self.cfg=SimpleNamespace(network=SimpleNamespace(**json.loads(path.read_bytes())))
    def test_through_service_is_in_denominator_not_north_count(self):
        r=next(x for x in self.doc["rows"] if x["eligible"])
        self.assertEqual(len(r["prefix"]),9);self.assertEqual(r["north_count"],8)
        self.assertEqual(r["prefix"][0]["turn"],"10241")
        self.assertAlmostEqual(c.rate_from_support(self.doc,2400),3600*8/(r["prefix"][-1]["time"]-r["start"]))
    def test_aliases_share_one_budget_and_other_fields_stay(self):
        before=copy.deepcopy(vars(self.cfg.network));rate=c.install(self.cfg,2400,self.doc)["rate"]
        after=vars(self.cfg.network)
        self.assertEqual({k for k in before if before[k]!=after[k]},{"regular_alias_pool","movement_capacity_by_movement_veh_h"})
        limits={};used={}
        for m in c.west.MEMBERS:service.register_limit(limits,c.west.GROUP,rate,10/3600,1)
        out=[]
        for m in c.west.MEMBERS:
            n=service.limit_one(100,c.west.GROUP,limits,used);service.accepted(n,c.west.GROUP,limits,used);out.append(n)
        self.assertAlmostEqual(sum(out),rate*10/3600)
        self.assertEqual(self.cfg.network.local_service_pool,before["local_service_pool"])
    def test_reject_future_or_rebound_group(self):
        bad=copy.deepcopy(self.doc);bad["window"][1]=2550
        with self.assertRaises(ValueError):c.rate_from_support(bad,2400)
        self.cfg.network.regular_alias_pool["groups"][c.west.GROUP]["phase"]="SC12_p3"
        with self.assertRaises(ValueError):c.install(self.cfg,2400,self.doc)
if __name__=="__main__":unittest.main()

