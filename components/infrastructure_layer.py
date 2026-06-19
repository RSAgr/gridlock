import folium

def add_infrastructure_layer(m, data):

    infra = data["infrastructure"]

    for hospital in infra["hospitals"]:

        folium.Marker(
            [hospital["lat"], hospital["lon"]],
            icon=folium.CustomIcon(
                "assets/icons/hospital.png",
                icon_size=(22,22)
            )
        ).add_to(m)

    for school in infra["schools"]:

        folium.Marker(
            [school["lat"], school["lon"]],
            icon=folium.CustomIcon(
                "assets/icons/school.png",
                icon_size=(22,22)
            )
        ).add_to(m)

    for fire in infra["fire_stations"]:

        folium.Marker(
            [fire["lat"], fire["lon"]],
            icon=folium.CustomIcon(
                "assets/icons/fire-station.png",
                icon_size=(22,22)
            )
        ).add_to(m)

    for police_station in infra["police_stations"]:

        folium.Marker(
            [police_station["lat"], police_station["lon"]],
            icon=folium.CustomIcon(
                "assets/icons/police-station.png",
                icon_size=(22,22)
            )
        ).add_to(m)