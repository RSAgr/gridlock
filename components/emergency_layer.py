import folium

def add_emergency_layer(m, data):

    for corridor in data["emergency_corridors"]:

        folium.PolyLine(
            corridor["route"],
            color="#16a34a",
            weight=4,
            dash_array="10,10"
        ).add_to(m)