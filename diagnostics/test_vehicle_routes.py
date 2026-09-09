"""Actual VBS route collector with fake COM; strict Python consumer checks."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from evaluation.controllers.vehicle_routes import ATTRIBUTES, complete_vehicle_routes
from scripts.tests.test_b1a_vbs_verified_capture_static import procedure

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT/'scripts/run_real_world_stackelberg_controller.vbs'


def physical(envelope):
    records = [dict(veh_no=k, link_no=56, lane_no=1, position_m=300., speed_kph=40., stopped=False) for k in (9, 20)]
    return {'sim_sec': 900., 'vehicle_routes': envelope, 'vehicle_records': {
        'complete': True, 'collection_count_before': 2, 'collection_count_after': 2, 'record_count': 2,
        'capture_sim_sec_before': 900., 'capture_sim_sec_after': 900.,
        'full_network_link_counts': {'56': 2}, 'records': records}}


def harness_source():
    source = RUNNER.read_text(encoding='utf-8-sig')
    helpers = '\n\n'.join(procedure(source, name) for name in (
        'VehicleRoutesJson', 'TryPositiveLongVariant', 'TryB1aLongVariant',
        'TryExact2DTableBounds', 'IsB1aEmptyTableResult', 'JsonEscape',
        'JsonDoubleInvariant', 'B1aSignificantDigitCount'))
    return r'''Option Explicit
Dim Vissim, JSON_DECIMAL_SEPARATOR, failureCode, mode, result, expected
JSON_DECIMAL_SEPARATOR = Mid(FormatNumber(1.5, 1, -1, 0, 0), 2, 1)
Class MockSimulation
    Public Function AttValue(attributeName)
        AttValue = CDbl(900)
        If mode = "time" Then AttValue = CDbl(901)
    End Function
End Class
Class MockVehicles
    Public Property Get Count()
        Count = 2
        If mode = "count" Then Count = 3
        If mode = "empty" Then Count = 0
    End Property
    Public Function GetMultiAttValues(attributeName)
        Dim table(1,1), value
        table(0,0) = 1: table(1,0) = 2
        Select Case attributeName
            Case "No": table(0,1) = 9: table(1,1) = 20
            Case "RoutDecNo": table(0,1) = 1129: table(1,1) = Empty
            Case "RouteNo": table(0,1) = 2: table(1,1) = Empty
            Case "RoutDecType": table(0,1) = "STATIC": table(1,1) = Empty
            Case Else: Err.Raise 5
        End Select
        If mode = "row" And attributeName = "RouteNo" Then table(0,0) = 99
        If mode = "id" And attributeName = "No" Then table(0,1) = 10
        If mode = "duplicate" And attributeName = "No" Then table(1,1) = 9
        If mode = "partial" And attributeName = "RouteNo" Then table(0,1) = Empty
        If mode = "noninteger" And attributeName = "RouteNo" Then table(0,1) = CDbl(2.5)
        If mode = "comerror" And attributeName = "RouteNo" Then Err.Raise 5, "Mock", "Injected COM failure"
        If mode = "empty" Then
            GetMultiAttValues = Empty
        Else
            GetMultiAttValues = table
        End If
    End Function
End Class
Class MockNet
    Public Vehicles
    Private Sub Class_Initialize()
        Set Vehicles = New MockVehicles
    End Sub
End Class
Class MockVissim
    Public Simulation, Net
    Private Sub Class_Initialize()
        Set Simulation = New MockSimulation
        Set Net = New MockNet
    End Sub
End Class
Sub RecordVehicleCaptureFailure(code, detail)
    failureCode = code
End Sub
Set Vissim = New MockVissim
expected = Array(20, 9)
For Each mode In Array("valid", "row", "id", "duplicate", "partial", "noninteger", "comerror", "time", "count", "empty")
    failureCode = ""
    If mode = "empty" Then
        result = VehicleRoutesJson(900, 0, Empty)
    Else
        result = VehicleRoutesJson(900, 2, expected)
    End If
    If IsEmpty(result) Then
        WScript.Echo mode & "|FAIL|" & failureCode
    Else
        WScript.Echo mode & "|PASS|" & result
    End If
Next
''' + helpers


class VehicleRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix='route-capture-', dir=ROOT/'diagnostics') as folder:
            invocation = Path(folder)/'invocation.vbs'
            invocation.write_text(harness_source(), encoding='utf-16')
            result = subprocess.run(['cscript.exe', '//nologo', str(invocation)], cwd=ROOT,
                                    capture_output=True, text=True, errors='replace', timeout=30)
            if result.returncode:
                raise AssertionError(result.stderr + result.stdout)
            cls.results = {mode: (status, payload) for mode, status, payload in
                           (line.split('|', 2) for line in result.stdout.splitlines())}
        cls.raw = physical(json.loads(cls.results['valid'][1]))

    def test_actual_collector_preserves_current_route_and_missing(self):
        routes = complete_vehicle_routes(self.raw, required=True)
        self.assertEqual(routes[9]['route_decision_no'], 1129)
        self.assertEqual(routes[9]['route_no'], 2)
        self.assertIsNone(routes[20]['route_no'])
        self.assertEqual(self.raw['vehicle_routes']['source_attributes'], ATTRIBUTES)

    def test_actual_collector_rejects_wrong_identity_alignment_and_capture(self):
        for mode in ('row', 'id', 'duplicate', 'partial', 'noninteger', 'comerror', 'time', 'count'):
            with self.subTest(mode=mode):
                self.assertEqual(self.results[mode][0], 'FAIL')
                self.assertTrue(self.results[mode][1])

    def test_actual_collector_empty_snapshot(self):
        status, payload = self.results['empty']
        self.assertEqual(status, 'PASS')
        self.assertEqual(json.loads(payload)['records'], [])

    def test_consumer_rejects_changed_time_and_id_set(self):
        for key, value in [('sim_sec_after', 901.), ('record_count', 1), ('complete', False)]:
            raw = copy.deepcopy(self.raw)
            raw['vehicle_routes'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                complete_vehicle_routes(raw)
        raw = copy.deepcopy(self.raw)
        raw['vehicle_routes']['records'][0]['veh_no'] = 10
        with self.assertRaises(ValueError):
            complete_vehicle_routes(raw)

    def test_consumer_rejects_partial_and_boolean_route(self):
        for value in (None, True, 0, -1):
            raw = copy.deepcopy(self.raw)
            raw['vehicle_routes']['records'][0]['route_no'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                complete_vehicle_routes(raw)

    def test_absent_capture_keeps_legacy_input_optional(self):
        raw = copy.deepcopy(self.raw)
        raw.pop('vehicle_routes')
        self.assertIsNone(complete_vehicle_routes(raw))
        with self.assertRaises(ValueError):
            complete_vehicle_routes(raw, required=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
