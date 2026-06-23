import folium

def add_diversion_layer(m, data):

    for route in data["diversions"]:

        blocked_route = route.get("blocked_route", [])
        alternate_route = route.get("alternate_route", [])
        route_color = route.get("route_color", "#dc2626")
        diversion_color = route.get("diversion_color", "#93c5fd")

        if len(blocked_route) > 1:
            folium.PolyLine(
                blocked_route,
                color=route_color,
                weight=5,
                opacity=0.95,
                dash_array="10,10"
            ).add_to(m)

        if len(alternate_route) > 1:
            folium.PolyLine(
                alternate_route,
                color=diversion_color,
                weight=5,
                opacity=0.85
            ).add_to(m)

    for barricade in data["deployment"]["barricades"]:

        folium.Marker(
            [barricade["lat"], barricade["lon"]],
            icon=folium.CustomIcon(
                "assets/icons/traffic-cone.png",
                icon_size=(22,22)
            )
        ).add_to(m)
