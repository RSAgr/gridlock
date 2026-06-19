import folium

def get_zone_style(level):

    if level == "Critical":
        return {
            "color": "#dc2626",
            "fillColor": "#ef4444",
            "fillOpacity": 0.35
        }

    elif level == "High":
        return {
            "color": "#ea580c",
            "fillColor": "#f97316",
            "fillOpacity": 0.25
        }

    return {
        "color": "#22c55e",
        "fillColor": "#22c55e",
        "fillOpacity": 0.15
    }


def add_critical_zone_layer(m, data):

    for zone in data["critical_zones"]:

        style = get_zone_style(
            zone["risk_level"]
        )

        folium.Polygon(
            locations=zone["polygon"],
            color=style["color"],
            fill=True,
            fill_color=style["fillColor"],
            fill_opacity=style["fillOpacity"],
            popup=f"""
            <b>{zone['name']}</b><br>
            Risk Level: {zone['risk_level']}
            """
        ).add_to(m)