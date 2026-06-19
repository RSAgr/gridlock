import folium

def get_junction_color(level):

    if level == "Critical":
        return "#dc2626"

    elif level == "High":
        return "#f97316"

    elif level == "Moderate":
        return "#eab308"

    return "#22c55e"


def add_junction_layer(m, data):

    for junction in data["junctions"]:

        color = get_junction_color(
            junction["risk_level"]
        )

        folium.CircleMarker(
            location=[
                junction["lat"],
                junction["lon"]
            ],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=f"""
            <b>{junction['name']}</b><br>
            Risk Level: {junction['risk_level']}<br>
            Risk Score: {junction['risk_score']}
            """
        ).add_to(m)