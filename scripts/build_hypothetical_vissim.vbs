Option Explicit

If WScript.Arguments.Count < 1 Then
    WScript.Echo "Usage: cscript build_hypothetical_vissim.vbs <target-directory>"
    WScript.Quit 2
End If

Dim targetDir
targetDir = WScript.Arguments(0)

Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FolderExists(targetDir) Then
    WScript.Echo "Target directory does not exist: " & targetDir
    WScript.Quit 3
End If

Dim netPath, layoutPath
netPath = fso.BuildPath(targetDir, "modi.inpx")
layoutPath = fso.BuildPath(targetDir, "modi.layx")

Dim Vissim
Set Vissim = CreateObject("Vissim.Vissim")
Vissim.New

Dim unitAttr
For Each unitAttr In Array("UnitAccel", "UnitLenLong", "UnitLenShort", "UnitLenVeryShort", "UnitSpeed", "UnitSpeedSmall")
    Vissim.Net.NetPara.AttValue(unitAttr) = 0
Next

Dim urbanWidths(1), freewayWidths(1), rampWidths(0)
urbanWidths(0) = 3.5
urbanWidths(1) = 3.5
freewayWidths(0) = 3.65
freewayWidths(1) = 3.65
rampWidths(0) = 4.0

Dim coordX, coordY, coordZ, nodeTrim, links, startX, startY, startZ, endX, endY, endZ
Set coordX = CreateObject("Scripting.Dictionary")
Set coordY = CreateObject("Scripting.Dictionary")
Set coordZ = CreateObject("Scripting.Dictionary")
Set nodeTrim = CreateObject("Scripting.Dictionary")
Set links = CreateObject("Scripting.Dictionary")
Set startX = CreateObject("Scripting.Dictionary")
Set startY = CreateObject("Scripting.Dictionary")
Set startZ = CreateObject("Scripting.Dictionary")
Set endX = CreateObject("Scripting.Dictionary")
Set endY = CreateObject("Scripting.Dictionary")
Set endZ = CreateObject("Scripting.Dictionary")

AddPoint "A", -600, 500, 0, 32
AddPoint "B", 0, 500, 0, 32
AddPoint "C", 600, 500, 0, 32
AddPoint "D", -600, 0, 0, 32
AddPoint "E", 0, 0, 0, 32
AddPoint "F", 600, 0, 0, 32

AddPoint "AW", -1120, 500, 0, 0
AddPoint "AN", -600, 980, 0, 0
AddPoint "BN", 0, 980, 0, 0
AddPoint "CN", 600, 980, 0, 0
AddPoint "CE", 1120, 500, 0, 0
AddPoint "DW", -1120, 0, 0, 0
AddPoint "FE", 1120, 0, 0, 0

' The trumpet stems pass over the freeway and end below it, matching a classic
' trumpet silhouette when viewed in 2D.
AddPoint "DT", -600, -700, 6, 0
AddPoint "FT", 600, -700, 6, 0

' Urban grid and external approaches.
AddRoadPair "AW", "A", "A west boundary", 0
AddRoadPair "AN", "A", "A north boundary", 0
AddRoadPair "A", "B", "A-B arterial", 2
AddRoadPair "A", "D", "A-D arterial", -2
AddRoadPair "BN", "B", "B north boundary", 0
AddRoadPair "B", "C", "B-C arterial", -2
AddRoadPair "B", "E", "B-E arterial", 2
AddRoadPair "CN", "C", "C north boundary", 0
AddRoadPair "C", "CE", "C east boundary", 0
AddRoadPair "C", "F", "C-F arterial", -2
AddRoadPair "DW", "D", "D west boundary", 0
AddRoadPair "D", "E", "D-E arterial", 2
AddRoadPair "D", "DT", "D trumpet stem", -5
AddRoadPair "E", "F", "E-F arterial", -2
AddRoadPair "F", "FE", "F east boundary", 0
AddRoadPair "F", "FT", "F trumpet stem", 6

' Urban intersection movements. E is intentionally an uncontrolled T junction.
AddIntersectionMovements "A", Array("AW", "AN", "B", "D")
AddIntersectionMovements "B", Array("A", "BN", "C", "E")
AddIntersectionMovements "C", Array("B", "CN", "CE", "F")
AddIntersectionMovements "D", Array("A", "DW", "E", "DT")
AddIntersectionMovements "E", Array("B", "D", "F")
AddIntersectionMovements "F", Array("C", "E", "FE", "FT")

' Divided freeway, eastbound and westbound carriageways.
Dim fwEB, fwWB
Set fwEB = Vissim.Net.Links.AddLink(0, Cubic3DWkt(-1450, -512, 0, -500, -515, 0, 500, -509, 0, 1450, -512, 0, 36, True), freewayWidths)
SetName fwEB, "FW_E eastbound mainline"
Set fwWB = Vissim.Net.Links.AddLink(0, Cubic3DWkt(1450, -488, 0, 500, -485, 0, -500, -491, 0, -1450, -488, 0, 36, True), freewayWidths)
SetName fwWB, "FW_W westbound mainline"

' D and F classic trumpet interchanges. D opens to the west; F is mirrored to the east.
BuildTrumpet "D", -600, -610, 112, fwEB, fwWB, -1
BuildTrumpet "F", 600, -610, 112, fwEB, fwWB, 1

' Evaluation nodes around the six urban junctions.
AddEvalNode "A", -600, 500, 48
AddEvalNode "B", 0, 500, 48
AddEvalNode "C", 600, 500, 48
AddEvalNode "D", -600, 0, 48
AddEvalNode "E", 0, 0, 48
AddEvalNode "F", 600, 0, 48
AddEvalNode "D trumpet", -600, -590, 270
AddEvalNode "F trumpet", 600, -590, 270

' Boundary vehicle inputs are created with zero demand. Scenario/controller scripts can set them.
AddVehicleInput "VI_A_W", "AW", "A", 0
AddVehicleInput "VI_A_N", "AN", "A", 0
AddVehicleInput "VI_B_N", "BN", "B", 0
AddVehicleInput "VI_C_N", "CN", "C", 0
AddVehicleInput "VI_C_E", "CE", "C", 0
AddVehicleInput "VI_D_W", "DW", "D", 0
AddVehicleInput "VI_F_E", "FE", "F", 0
AddVehicleInputOnLink "VI_FW_E", fwEB, 0
AddVehicleInputOnLink "VI_FW_W", fwWB, 0

' Queue counters at urban approaches and trumpet stems.
Dim approachPairs, p
approachPairs = Array( _
    Array("AW", "A"), Array("AN", "A"), Array("B", "A"), Array("D", "A"), _
    Array("A", "B"), Array("BN", "B"), Array("C", "B"), Array("E", "B"), _
    Array("B", "C"), Array("CN", "C"), Array("CE", "C"), Array("F", "C"), _
    Array("A", "D"), Array("DW", "D"), Array("E", "D"), Array("DT", "D"), _
    Array("B", "E"), Array("D", "E"), Array("F", "E"), _
    Array("C", "F"), Array("E", "F"), Array("FE", "F"), Array("FT", "F") _
)
For Each p In approachPairs
    AddQueueAtEnd "QC_" & p(0) & "_" & p(1), links.Item(LinkKey(p(0), p(1))), 12
Next

' Mainline density/flow observation points around both interchanges.
AddFreewayDetectors "FW_E", fwEB, Array(250, 550, 850, 1150, 1450, 1750, 2050, 2350, 2650)
AddFreewayDetectors "FW_W", fwWB, Array(250, 550, 850, 1150, 1450, 1750, 2050, 2350, 2650)

' Urban MFD observation points on all internal bidirectional roads.
Dim internalPairs
internalPairs = Array( _
    Array("A", "B"), Array("B", "C"), Array("A", "D"), Array("B", "E"), _
    Array("C", "F"), Array("D", "E"), Array("E", "F") _
)
For Each p In internalPairs
    AddMidLinkDetectors "URB_" & p(0) & "_" & p(1), links.Item(LinkKey(p(0), p(1)))
    AddMidLinkDetectors "URB_" & p(1) & "_" & p(0), links.Item(LinkKey(p(1), p(0)))
Next

Vissim.Simulation.AttValue("SimPeriod") = 7200
Vissim.Simulation.AttValue("RandSeed") = 42
Vissim.Graphics.CurrentNetworkWindow.ZoomTo -1500, -750, 1500, 1050
On Error Resume Next
Vissim.Graphics.CurrentNetworkWindow.AttValue("QuickMode") = 1
Vissim.Graphics.CurrentNetworkWindow.AttValue("ShowMap") = False
Err.Clear
On Error GoTo 0

Vissim.SaveNetAs netPath
Vissim.SaveLayout layoutPath
DisableMapInLayout layoutPath

WScript.Echo "NETWORK=" & netPath
WScript.Echo "LAYOUT=" & layoutPath
WScript.Echo "LINKS=" & Vissim.Net.Links.Count
WScript.Echo "NODES=" & Vissim.Net.Nodes.Count
WScript.Echo "VEHICLE_INPUTS=" & Vissim.Net.VehicleInputs.Count
WScript.Echo "QUEUE_COUNTERS=" & Vissim.Net.QueueCounters.Count
WScript.Echo "DATA_COLLECTION_POINTS=" & Vissim.Net.DataCollectionPoints.Count

Set Vissim = Nothing
WScript.Quit 0

Sub AddPoint(name, x, y, z, trim)
    coordX.Add name, CDbl(x)
    coordY.Add name, CDbl(y)
    coordZ.Add name, CDbl(z)
    nodeTrim.Add name, CDbl(trim)
End Sub

Function LinkKey(a, b)
    LinkKey = a & ">" & b
End Function

Function Num(v)
    Num = Replace(CStr(Round(CDbl(v), 3)), ",", ".")
End Function

Function Point3(x, y, z)
    Point3 = Num(x) & " " & Num(y) & " " & Num(z)
End Function

Function CubicValue(p0, p1, p2, p3, t)
    CubicValue = ((1 - t) ^ 3) * p0 + 3 * ((1 - t) ^ 2) * t * p1 + 3 * (1 - t) * (t ^ 2) * p2 + (t ^ 3) * p3
End Function

Function Cubic3DWkt(x0, y0, z0, x1, y1, z1, x2, y2, z2, x3, y3, z3, segments, includeEnds)
    Dim firstI, lastI, i, t, s, x, y, z
    If includeEnds Then
        firstI = 0
        lastI = segments
    Else
        firstI = 1
        lastI = segments - 1
    End If

    s = "LINESTRING("
    For i = firstI To lastI
        t = CDbl(i) / CDbl(segments)
        x = CubicValue(x0, x1, x2, x3, t)
        y = CubicValue(y0, y1, y2, y3, t)
        z = CubicValue(z0, z1, z2, z3, t)
        If i > firstI Then s = s & ","
        s = s & Point3(x, y, z)
    Next
    s = s & ")"
    Cubic3DWkt = s
End Function

Sub AddRoadPair(a, b, baseName, bend)
    AddDirectedRoad a, b, baseName & " " & a & " to " & b, bend
    AddDirectedRoad b, a, baseName & " " & b & " to " & a, -bend
End Sub

Sub AddDirectedRoad(a, b, linkName, bend)
    Dim ax, ay, az, bx, by, bz, dx, dy, dz, length, ux, uy, rx, ry
    Dim sx, sy, sz, ex, ey, ez, c1x, c1y, c1z, c2x, c2y, c2z, key, link
    ax = coordX.Item(a)
    ay = coordY.Item(a)
    az = coordZ.Item(a)
    bx = coordX.Item(b)
    by = coordY.Item(b)
    bz = coordZ.Item(b)
    dx = bx - ax
    dy = by - ay
    dz = bz - az
    length = Sqr(dx * dx + dy * dy)
    ux = dx / length
    uy = dy / length
    rx = uy
    ry = -ux

    sx = ax + ux * nodeTrim.Item(a) + rx * 5
    sy = ay + uy * nodeTrim.Item(a) + ry * 5
    sz = az + dz * nodeTrim.Item(a) / length
    ex = bx - ux * nodeTrim.Item(b) + rx * 5
    ey = by - uy * nodeTrim.Item(b) + ry * 5
    ez = bz - dz * nodeTrim.Item(b) / length

    c1x = sx + (ex - sx) / 3 + rx * bend
    c1y = sy + (ey - sy) / 3 + ry * bend
    c1z = sz + (ez - sz) / 3
    c2x = sx + 2 * (ex - sx) / 3 + rx * bend
    c2y = sy + 2 * (ey - sy) / 3 + ry * bend
    c2z = sz + 2 * (ez - sz) / 3

    Set link = Vissim.Net.Links.AddLink(0, Cubic3DWkt(sx, sy, sz, c1x, c1y, c1z, c2x, c2y, c2z, ex, ey, ez, 14, True), urbanWidths)
    SetName link, linkName

    key = LinkKey(a, b)
    links.Add key, link
    startX.Add key, sx
    startY.Add key, sy
    startZ.Add key, sz
    endX.Add key, ex
    endY.Add key, ey
    endZ.Add key, ez
End Sub

Sub AddIntersectionMovements(nodeName, neighborNames)
    Dim fromName, toName
    For Each fromName In neighborNames
        For Each toName In neighborNames
            If CStr(fromName) <> CStr(toName) Then
                AddMovement CStr(fromName), nodeName, CStr(toName)
            End If
        Next
    Next
End Sub

Sub AddMovement(fromName, nodeName, toName)
    Dim inKey, outKey, inLink, outLink, inUx, inUy, outUx, outUy, inLen, outLen
    Dim cross, dot, movement, fromLaneNo, toLaneNo, laneCount, controlDist
    Dim sx, sy, sz, ex, ey, ez, c1x, c1y, c1z, c2x, c2y, c2z, wkt, conn

    inKey = LinkKey(fromName, nodeName)
    outKey = LinkKey(nodeName, toName)
    Set inLink = links.Item(inKey)
    Set outLink = links.Item(outKey)

    inUx = coordX.Item(nodeName) - coordX.Item(fromName)
    inUy = coordY.Item(nodeName) - coordY.Item(fromName)
    inLen = Sqr(inUx * inUx + inUy * inUy)
    inUx = inUx / inLen
    inUy = inUy / inLen

    outUx = coordX.Item(toName) - coordX.Item(nodeName)
    outUy = coordY.Item(toName) - coordY.Item(nodeName)
    outLen = Sqr(outUx * outUx + outUy * outUy)
    outUx = outUx / outLen
    outUy = outUy / outLen

    cross = inUx * outUy - inUy * outUx
    dot = inUx * outUx + inUy * outUy

    If dot > 0.7 Then
        movement = "TH"
        fromLaneNo = 1
        toLaneNo = 1
        laneCount = 2
        controlDist = 21
    ElseIf cross < 0 Then
        movement = "RT"
        fromLaneNo = 1
        toLaneNo = 1
        laneCount = 1
        controlDist = 16
    Else
        movement = "LT"
        fromLaneNo = 2
        toLaneNo = 2
        laneCount = 1
        controlDist = 29
    End If

    sx = endX.Item(inKey)
    sy = endY.Item(inKey)
    sz = endZ.Item(inKey)
    ex = startX.Item(outKey)
    ey = startY.Item(outKey)
    ez = startZ.Item(outKey)
    c1x = sx + inUx * controlDist
    c1y = sy + inUy * controlDist
    c1z = sz
    c2x = ex - outUx * controlDist
    c2y = ey - outUy * controlDist
    c2z = ez
    wkt = Cubic3DWkt(sx, sy, sz, c1x, c1y, c1z, c2x, c2y, c2z, ex, ey, ez, 10, False)

    Set conn = Vissim.Net.Links.AddConnector(0, inLink.Lanes.ItemByKey(fromLaneNo), inLink.AttValue("Length2D"), outLink.Lanes.ItemByKey(toLaneNo), 0, laneCount, wkt)
    SetName conn, nodeName & " " & fromName & "-" & movement & "-" & toName
End Sub

Sub BuildTrumpet(tag, stemX, loopCy, loopR, ebLink, wbLink, side)
    Dim stemSouth, stemNorth, sbKey, nbKey
    sbKey = LinkKey(tag, tag & "T")
    nbKey = LinkKey(tag & "T", tag)
    Set stemSouth = links.Item(sbKey)
    Set stemNorth = links.Item(nbKey)

    Dim loopRamp, directOn, fromEB, fromWB
    Dim throatSX, throatSY, throatSZ, throatNX, throatNY, throatNZ
    Dim loopMergeX, loopMergeY, directMergeX, directMergeY, xEbOff, xWbOff
    Dim loopEndX, loopEndY, directEndX, directEndY

    throatSX = endX.Item(sbKey)
    throatSY = endY.Item(sbKey)
    throatSZ = endZ.Item(sbKey)
    throatNX = startX.Item(nbKey)
    throatNY = startY.Item(nbKey)
    throatNZ = startZ.Item(nbKey)

    ' side=-1: loop opens to the west and merges to westbound.
    ' side=+1: loop opens to the east and merges to eastbound.
    loopMergeX = stemX + side * 430
    directMergeX = stemX - side * 430
    xEbOff = stemX - 430
    xWbOff = stemX + 430

    If side < 0 Then
        loopMergeY = -488
        directMergeY = -512
    Else
        loopMergeY = -512
        directMergeY = -488
    End If

    loopEndX = loopMergeX - side * 92
    loopEndY = loopMergeY + side * 0
    directEndX = directMergeX - (-side) * 92
    If side < 0 Then
        directEndY = -535
    Else
        directEndY = -465
    End If

    Set loopRamp = Vissim.Net.Links.AddLink(0, TrumpetLoopWkt(stemX, throatSY, loopCy, loopR, side, loopEndX, loopEndY), rampWidths)
    SetName loopRamp, tag & " classic trumpet loop ramp"

    Set directOn = Vissim.Net.Links.AddLink(0, Cubic3DWkt( _
        throatSX - side * 14, throatSY + 4, throatSZ, _
        stemX - side * 42, throatSY + 84, 4.6, _
        stemX - side * 250, directEndY - 34, 1.3, _
        directEndX, directEndY, 0.4, 18, True), rampWidths)
    SetName directOn, tag & " classic trumpet direct on-ramp"

    Set fromEB = Vissim.Net.Links.AddLink(0, Cubic3DWkt( _
        xEbOff + 94, -535, 0.4, _
        stemX - 245, -545, 1.1, _
        stemX - 84, throatSY + 96, 4.9, _
        throatNX - 10, throatNY + 10, throatNZ, 18, True), rampWidths)
    SetName fromEB, tag & " classic trumpet FW_E off-ramp"

    Set fromWB = Vissim.Net.Links.AddLink(0, Cubic3DWkt( _
        xWbOff - 94, -465, 0.4, _
        stemX + 245, -455, 1.1, _
        stemX + 84, throatSY + 96, 4.9, _
        throatNX + 10, throatNY + 10, throatNZ, 18, True), rampWidths)
    SetName fromWB, tag & " classic trumpet FW_W off-ramp"

    AddCurvedConnector tag & " stem to loop throat", stemSouth.Lanes.ItemByKey(2), stemSouth.AttValue("Length2D"), loopRamp.Lanes.ItemByKey(1), 0, throatSX, throatSY, throatSZ, 0, -1, stemX + side * 24, throatSY + 18, throatSZ, side, 1, 18
    AddCurvedConnector tag & " stem to direct throat", stemSouth.Lanes.ItemByKey(1), stemSouth.AttValue("Length2D"), directOn.Lanes.ItemByKey(1), 0, throatSX, throatSY, throatSZ, 0, -1, throatSX - side * 14, throatSY + 4, throatSZ, -side, 1, 16

    If side < 0 Then
        AddCurvedConnector tag & " loop WB merge taper", loopRamp.Lanes.ItemByKey(1), loopRamp.AttValue("Length2D"), wbLink.Lanes.ItemByKey(1), WestboundPos(loopMergeX), loopEndX, loopEndY, 0.2, -1, 0, loopMergeX, -488, 0, -1, 0, 64
        AddCurvedConnector tag & " direct EB merge taper", directOn.Lanes.ItemByKey(1), directOn.AttValue("Length2D"), ebLink.Lanes.ItemByKey(1), EastboundPos(directMergeX), directEndX, directEndY, 0.2, 1, 0, directMergeX, -512, 0, 1, 0, 64
    Else
        AddCurvedConnector tag & " loop EB merge taper", loopRamp.Lanes.ItemByKey(1), loopRamp.AttValue("Length2D"), ebLink.Lanes.ItemByKey(1), EastboundPos(loopMergeX), loopEndX, loopEndY, 0.2, 1, 0, loopMergeX, -512, 0, 1, 0, 64
        AddCurvedConnector tag & " direct WB merge taper", directOn.Lanes.ItemByKey(1), directOn.AttValue("Length2D"), wbLink.Lanes.ItemByKey(1), WestboundPos(directMergeX), directEndX, directEndY, 0.2, -1, 0, directMergeX, -488, 0, -1, 0, 64
    End If

    AddCurvedConnector tag & " FW_E diverge taper", ebLink.Lanes.ItemByKey(1), EastboundPos(xEbOff), fromEB.Lanes.ItemByKey(1), 0, xEbOff, -512, 0, 1, 0, xEbOff + 94, -535, 0.4, 1, 0, 48
    AddCurvedConnector tag & " FW_W diverge taper", wbLink.Lanes.ItemByKey(1), WestboundPos(xWbOff), fromWB.Lanes.ItemByKey(1), 0, xWbOff, -488, 0, -1, 0, xWbOff - 94, -465, 0.4, -1, 0, 48

    AddCurvedConnector tag & " FW_E ramp into stem", fromEB.Lanes.ItemByKey(1), fromEB.AttValue("Length2D"), stemNorth.Lanes.ItemByKey(1), 0, throatNX - 10, throatNY + 10, throatNZ, 0, 1, throatNX, throatNY, throatNZ, 0, 1, 16
    AddCurvedConnector tag & " FW_W ramp into stem", fromWB.Lanes.ItemByKey(1), fromWB.AttValue("Length2D"), stemNorth.Lanes.ItemByKey(2), 0, throatNX + 10, throatNY + 10, throatNZ, 0, 1, throatNX, throatNY, throatNZ, 0, 1, 16

    AddQueueAtEnd "QC_" & tag & "_LOOP", loopRamp, 35
    AddQueueAtEnd "QC_" & tag & "_DIRECT_ON", directOn, 35
    AddMidLinkDetectors "RAMP_" & tag & "_LOOP", loopRamp
    AddMidLinkDetectors "RAMP_" & tag & "_DIRECT_ON", directOn
    AddMidLinkDetectors "RAMP_" & tag & "_EB_OFF", fromEB
    AddMidLinkDetectors "RAMP_" & tag & "_WB_OFF", fromWB
End Sub

Function TrumpetLoopWkt(stemX, throatY, cy, radius, side, endXValue, endYValue)
    Dim s, startRampX, startRampY, cx, i, angle, startAngle, endAngle, x, y, z, piValue
    Dim arcStartX, arcStartY, arcEndX, arcEndY, t, bx, by, bz
    piValue = 4 * Atn(1)
    cx = stemX + side * (radius + 55)
    startRampX = stemX + side * 24
    startRampY = throatY + 18
    s = "LINESTRING(" & Point3(startRampX, startRampY, 5.8)

    If side < 0 Then
        startAngle = 0
        endAngle = -1.25 * piValue
    Else
        startAngle = piValue
        endAngle = 2.25 * piValue
    End If

    arcStartX = cx + radius * Cos(startAngle)
    arcStartY = cy + radius * Sin(startAngle)

    ' Smooth approach from the trumpet neck to the near side of the large loop.
    For i = 1 To 6
        t = CDbl(i) / 6
        bx = CubicValue(startRampX, startRampX + side * 28, arcStartX - side * 35, arcStartX, t)
        by = CubicValue(startRampY, startRampY + 48, arcStartY - 30, arcStartY, t)
        bz = CubicValue(5.8, 5.5, 4.8, 4.3, t)
        s = s & "," & Point3(bx, by, bz)
    Next

    ' 225-degree loop, mirrored at D/F. This is the defining trumpet bulb.
    For i = 1 To 34
        angle = startAngle + (endAngle - startAngle) * CDbl(i) / 34
        x = cx + radius * Cos(angle)
        y = cy + radius * Sin(angle)
        z = 4.5 - 0.065 * i
        s = s & "," & Point3(x, y, z)
    Next

    arcEndX = cx + radius * Cos(endAngle)
    arcEndY = cy + radius * Sin(endAngle)
    For i = 1 To 14
        t = CDbl(i) / 14
        bx = CubicValue(arcEndX, arcEndX + side * 40, endXValue - side * 90, endXValue, t)
        by = CubicValue(arcEndY, arcEndY + 20, endYValue + 18, endYValue, t)
        bz = CubicValue(2.1, 1.8, 0.7, 0.2, t)
        s = s & "," & Point3(bx, by, bz)
    Next

    s = s & ")"
    TrumpetLoopWkt = s
End Function

Sub AddCurvedConnector(name, fromLane, fromPos, toLane, toPos, sx, sy, sz, h0x, h0y, ex, ey, ez, h1x, h1y, controlDist)
    Dim c1x, c1y, c2x, c2y, wkt, conn
    c1x = sx + h0x * controlDist
    c1y = sy + h0y * controlDist
    c2x = ex - h1x * controlDist
    c2y = ey - h1y * controlDist
    wkt = Cubic3DWkt(sx, sy, sz, c1x, c1y, sz, c2x, c2y, ez, ex, ey, ez, 10, False)
    Set conn = Vissim.Net.Links.AddConnector(0, fromLane, fromPos, toLane, toPos, 1, wkt)
    SetName conn, name
End Sub

Function EastboundPos(x)
    EastboundPos = x + 1450
End Function

Function WestboundPos(x)
    WestboundPos = 1450 - x
End Function

Sub AddEvalNode(name, cx, cy, halfSize)
    Dim polygon, n
    polygon = "POLYGON((" & Num(cx - halfSize) & " " & Num(cy - halfSize) & "," & _
        Num(cx + halfSize) & " " & Num(cy - halfSize) & "," & _
        Num(cx + halfSize) & " " & Num(cy + halfSize) & "," & _
        Num(cx - halfSize) & " " & Num(cy + halfSize) & "," & _
        Num(cx - halfSize) & " " & Num(cy - halfSize) & "))"
    Set n = Vissim.Net.Nodes.AddNode(0, polygon)
    SetName n, name
End Sub

Sub AddVehicleInput(name, a, b, volume)
    AddVehicleInputOnLink name, links.Item(LinkKey(a, b)), volume
End Sub

Sub AddVehicleInputOnLink(name, link, volume)
    Dim vi
    Set vi = Vissim.Net.VehicleInputs.AddVehicleInput(0, link)
    vi.AttValue("Volume(1)") = volume
    SetName vi, name
End Sub

Sub AddQueueAtEnd(name, link, distanceFromEnd)
    Dim pos, qc
    pos = link.AttValue("Length2D") - distanceFromEnd
    If pos < 1 Then pos = 1
    Set qc = Vissim.Net.QueueCounters.AddQueueCounter(0, link, pos)
    SetName qc, name
End Sub

Sub AddFreewayDetectors(prefix, link, positions)
    Dim pos, laneNo, dp
    For Each pos In positions
        For laneNo = 1 To 2
            Set dp = Vissim.Net.DataCollectionPoints.AddDataCollectionPoint(0, link.Lanes.ItemByKey(laneNo), CDbl(pos))
            SetName dp, prefix & "_" & CStr(pos) & "_L" & CStr(laneNo)
        Next
    Next
End Sub

Sub AddMidLinkDetectors(prefix, link)
    Dim pos, laneNo, dp
    pos = link.AttValue("Length2D") / 2
    For laneNo = 1 To link.Lanes.Count
        Set dp = Vissim.Net.DataCollectionPoints.AddDataCollectionPoint(0, link.Lanes.ItemByKey(laneNo), pos)
        SetName dp, prefix & "_L" & CStr(laneNo)
    Next
End Sub

Sub SetName(obj, name)
    On Error Resume Next
    obj.AttValue("Name") = name
    Err.Clear
    On Error GoTo 0
End Sub

Sub DisableMapInLayout(path)
    On Error Resume Next
    Dim ts, text
    Set ts = fso.OpenTextFile(path, 1, False)
    text = ts.ReadAll
    ts.Close
    text = Replace(text, "showMap=""true""", "showMap=""false""")
    Set ts = fso.OpenTextFile(path, 2, False)
    ts.Write text
    ts.Close
    Err.Clear
    On Error GoTo 0
End Sub
