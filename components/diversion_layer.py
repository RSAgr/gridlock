import folium

def add_diversion_layer(m, data):

    for route in data["diversions"]:

        folium.PolyLine(
            route["blocked_route"],
            color="#dc2626",
            weight=4,
            dash_array="10,10"
        ).add_to(m)

        folium.PolyLine(
            route["alternate_route"],
            color="#2563eb",
            weight=5
        ).add_to(m)

    for barricade in data["deployment"]["barricades"]:

        folium.Marker(
            [barricade["lat"], barricade["lon"]],
            icon=folium.CustomIcon(
                "assets/icons/traffic-cone.png",
                icon_size=(22,22)
            )
        ).add_to(m)