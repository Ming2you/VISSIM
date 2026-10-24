"""Add the exact production route collector to the native COM qualifier.

This generates a diagnostic harness only. No adapter or model is evaluated.
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.tests.test_b1a_vbs_verified_capture_static import procedure


def main():
    base = ROOT/'diagnostics/probe_vehicle_route_com.vbs'
    runner = ROOT/'scripts/run_real_world_stackelberg_controller.vbs'
    target = ROOT/'diagnostics/vehicle_route_collector_native_probe.vbs'
    if target.exists():
        raise FileExistsError(target)
    source = base.read_text(encoding='utf-8-sig')
    actual = runner.read_text(encoding='utf-8-sig')
    names = ('VehicleRoutesJson', 'TryPositiveLongVariant', 'TryB1aLongVariant',
             'TryExact2DTableBounds', 'IsB1aEmptyTableResult', 'JsonEscape',
             'JsonDoubleInvariant', 'B1aSignificantDigitCount')
    helpers = {name: procedure(actual, name) for name in names}
    replacements = {
        'Dim rowCount, value, laneParts, linkNo, selected, attrNo, stamps':
            'Dim rowCount, value, laneParts, linkNo, selected, attrNo, stamps\nDim Vissim, JSON_DECIMAL_SEPARATOR, routeOutput, physicalOutput',
        'names = Array("No", "Lane", "Pos", "RoutDecNo", "RouteNo", "RoutDecType")':
            '''names = Array("No", "Lane", "Pos", "RoutDecNo", "RouteNo", "RoutDecType")
Set Vissim = sim
JSON_DECIMAL_SEPARATOR = Mid(FormatNumber(1.5, 1, -1, 0, 0), 2, 1)
Set routeOutput = fs.CreateTextFile(WScript.Arguments(1) & ".jsonl", False, False)
Set physicalOutput = fs.CreateTextFile(WScript.Arguments(1) & ".physical.csv", False, False)
physicalOutput.WriteLine "sim_sec,veh_no,lane,pos_m,speed_kph"
CaptureProductionRoutes''',
        '    End If\nNext\noutput.Close':
            '    End If\n    If stepNo = 1 Or stepNo Mod 150 = 0 Then CaptureProductionRoutes\nNext\nrouteOutput.Close\nphysicalOutput.Close\nSet Vissim = Nothing\noutput.Close',
    }
    for old, new in replacements.items():
        if source.count(old) != 1:
            raise ValueError('Native qualifier changed: review the exact capture hook')
        source = source.replace(old, new)
    source += r'''

Sub RecordVehicleCaptureFailure(code, detail)
    WScript.Echo "COLLECTOR_FAILURE=" & code & " " & detail
    WScript.Quit 8
End Sub

Sub CaptureProductionRoutes()
    Dim n, sec, columns, table(3), attr, row, ids, captured, index
    n = Vissim.Net.Vehicles.Count
    sec = Vissim.Simulation.AttValue("SimSec")
    columns = Array("No", "Lane", "Pos", "Speed")
    ids = Empty
    If n > 0 Then
        ReDim ids(n-1)
        For attr = 0 To 3
            table(attr) = Vissim.Net.Vehicles.GetMultiAttValues(columns(attr))
            If UBound(table(attr),1)+1 <> n Then WScript.Quit 9
        Next
        For row = 0 To n-1
            For attr = 1 To 3
                If table(attr)(row,0) <> table(0)(row,0) Then WScript.Quit 10
            Next
            ids(row) = table(0)(row,1)
            physicalOutput.WriteLine JsonDoubleInvariant(sec) & "," & Csv(table(0)(row,1)) & "," & _
                Csv(table(1)(row,1)) & "," & Csv(table(2)(row,1)) & "," & Csv(table(3)(row,1))
        Next
    End If
    captured = VehicleRoutesJson(sec, n, ids)
    If IsEmpty(captured) Then WScript.Quit 11
    routeOutput.WriteLine captured
    WScript.Echo "COLLECTOR_SEC=" & JsonDoubleInvariant(sec) & " COUNT=" & CStr(n)
End Sub
'''
    source += '\n\n' + '\n\n'.join(helpers.values()) + '\n'
    target.write_text(source, encoding='utf-16')
    manifest = {'scope': 'Exact production route collector on native COM; independent physical ID/position reads, not full WriteStateJson or controller validation',
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (base, runner, Path(__file__), target)},
        'extracted_procedure_sha256': {name: hashlib.sha256(body.encode('utf-8')).hexdigest() for name, body in helpers.items()}}
    target.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'output': str(target), 'procedures': len(helpers)}))


if __name__ == '__main__':
    main()
