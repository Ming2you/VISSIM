def AddVehicle():
    vehType = 300
    link = 43
    lane = 1
    pos = 0
    desSpeed = 60
    Vissim.Net.Vehicles.AddVehicleAtLinkPosition(vehType, link, lane, pos, desSpeed)
