import folium

def add_deployment_layer(m, data):

    for officer in data["deployment"]["officers"]:

        folium.Marker(
            location=[
                officer["lat"],
                officer["lon"]
            ],
            popup=f"""
            Police Deployment
            <br>
            Officers: {officer['count']}
            """,
            icon=folium.CustomIcon(
                "assets/icons/policeman.png",
                icon_size=(22,22)
            )
        ).add_to(m)