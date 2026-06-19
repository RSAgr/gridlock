import folium

def add_event_layer(m, data):

    venue = data["event"]["venue"]

    folium.Marker(
        [venue["lat"], venue["lon"]],
        popup=f"""
        <b>{data['event']['name']}</b><br>
        {venue['name']}
        """
    ).add_to(m)

    folium.Circle(
        location=[
            venue["lat"],
            venue["lon"]
        ],
        radius=data["event"]["impact_radius"]*0.5,
        color="#2563eb",
        fill=True,
        fill_color="#3b82f6",
        fill_opacity=0.15,
        weight=2
    ).add_to(m)