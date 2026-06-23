import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MiniMap

st.set_page_config(
    page_title="Event Operations Command Center",
    layout="wide"
)

st.warning("This page is just for experimenting")

# =====================================================
# EVENT DATA
# =====================================================

VENUE = {
    "name": "Mekhri Circle",
    "lat": 13.0170,
    "lon": 77.5838
}

RADIUS = 500

PRIMARY_DIVERSION = {
    "name": "Malleswaram 18th Cross Rd - Sampige Rd Junction",
    "lat": 13.007195,
    "lon": 77.583160,
    "health": 0.98
}

SECONDARY_DIVERSION = {
    "name": "Bashyam Circle",
    "lat": 12.9926,
    "lon": 77.56459,
    "health": 0.97
}

AVOID_JUNCTION = {
    "name": "Sadashivnagar Junction",
    "lat": 13.0056,
    "lon": 77.5750,
    "health": 0.92
}

POLICE_STATIONS = [
    {
        "name": "Sadashivanagar Police Station",
        "lat": 13.014656,
        "lon": 77.572746,
        "officers": 2,
        "workload": 80
    },
    {
        "name": "Yeshwanthpura Police Station",
        "lat": 13.0189,
        "lon": 77.5581,
        "officers": 3,
        "workload": 15
    }
]

REQUIRED_OFFICERS = 5

# =====================================================
# HEADER
# =====================================================

st.title("🚦 Event Operations Command Center")

st.markdown(
    """
    Real-Time Traffic Management & Police Deployment Dashboard
    """
)

# =====================================================
# KPI CARDS
# =====================================================

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Venue", "Mekhri Circle")
c2.metric("Impact Radius", "500 m")
c3.metric("Required Officers", REQUIRED_OFFICERS)
c4.metric("Primary Diversion", "Available")
c5.metric("Avoid Routes", 1)

# =====================================================
# MAP
# =====================================================

m = folium.Map(
    location=[VENUE["lat"], VENUE["lon"]],
    zoom_start=14,
    control_scale=True
)

MiniMap().add_to(m)

# =====================================================
# FEATURE GROUPS
# =====================================================

event_layer = folium.FeatureGroup(name="Event Layer")
diversion_layer = folium.FeatureGroup(name="Diversions")
police_layer = folium.FeatureGroup(name="Police Deployment")
avoid_layer = folium.FeatureGroup(name="Avoid Routes")

# =====================================================
# EVENT MARKER
# =====================================================

folium.Marker(
    [VENUE["lat"], VENUE["lon"]],
    popup="""
    <b>Mekhri Circle</b><br>
    Event Venue<br>
    Required Officers: 5
    """,
    icon=folium.Icon(color="red", icon="flag")
).add_to(event_layer)

# =====================================================
# IMPACT RADIUS
# =====================================================

folium.Circle(
    radius=RADIUS,
    location=[VENUE["lat"], VENUE["lon"]],
    color="red",
    fill=True,
    fill_opacity=0.15,
    popup="500m Impact Radius"
).add_to(event_layer)

# =====================================================
# PRIMARY DIVERSION
# =====================================================

folium.Marker(
    [PRIMARY_DIVERSION["lat"], PRIMARY_DIVERSION["lon"]],
    popup=f"""
    <b>Primary Diversion</b><br>
    {PRIMARY_DIVERSION["name"]}<br>
    Health Score: {PRIMARY_DIVERSION["health"]}
    """,
    icon=folium.Icon(color="green")
).add_to(diversion_layer)

folium.PolyLine(
    [
        [VENUE["lat"], VENUE["lon"]],
        [PRIMARY_DIVERSION["lat"], PRIMARY_DIVERSION["lon"]]
    ],
    color="green",
    weight=6,
    tooltip="Primary Diversion"
).add_to(diversion_layer)

# =====================================================
# SECONDARY DIVERSION
# =====================================================

folium.Marker(
    [SECONDARY_DIVERSION["lat"], SECONDARY_DIVERSION["lon"]],
    popup=f"""
    <b>Secondary Diversion</b><br>
    {SECONDARY_DIVERSION["name"]}<br>
    Health Score: {SECONDARY_DIVERSION["health"]}
    """,
    icon=folium.Icon(color="blue")
).add_to(diversion_layer)

folium.PolyLine(
    [
        [VENUE["lat"], VENUE["lon"]],
        [SECONDARY_DIVERSION["lat"], SECONDARY_DIVERSION["lon"]]
    ],
    color="blue",
    weight=6,
    tooltip="Secondary Diversion"
).add_to(diversion_layer)

# =====================================================
# AVOID ROUTE
# =====================================================

folium.Marker(
    [AVOID_JUNCTION["lat"], AVOID_JUNCTION["lon"]],
    popup=f"""
    <b>AVOID ROUTE</b><br>
    {AVOID_JUNCTION["name"]}<br>
    Health Score: {AVOID_JUNCTION["health"]}
    """,
    icon=folium.Icon(color="darkred")
).add_to(avoid_layer)

folium.PolyLine(
    [
        [VENUE["lat"], VENUE["lon"]],
        [AVOID_JUNCTION["lat"], AVOID_JUNCTION["lon"]]
    ],
    color="red",
    weight=6,
    dash_array="10",
    tooltip="Avoid Route"
).add_to(avoid_layer)

# =====================================================
# POLICE STATIONS
# =====================================================

for station in POLICE_STATIONS:

    folium.Marker(
        [station["lat"], station["lon"]],
        popup=f"""
        <b>{station['name']}</b><br>
        Officers Allocated: {station['officers']}<br>
        Workload: {station['workload']}%
        """,
        icon=folium.Icon(color="black", icon="shield")
    ).add_to(police_layer)

    folium.PolyLine(
        [
            [station["lat"], station["lon"]],
            [VENUE["lat"], VENUE["lon"]]
        ],
        color="black",
        weight=4,
        dash_array="8",
        tooltip=f"{station['officers']} Officers Deployed"
    ).add_to(police_layer)

# =====================================================
# ADD LAYERS
# =====================================================

event_layer.add_to(m)
diversion_layer.add_to(m)
avoid_layer.add_to(m)
police_layer.add_to(m)

folium.LayerControl().add_to(m)

# =====================================================
# LEGEND
# =====================================================

legend = """
<div style="
position: fixed;
top: 80px,
right: 15px,
width: 200px;
background:white;
z-index:9999;
padding:10px;
border-radius:10px;
border:2px solid grey;
font-size:14px;
">
<b>Map Legend</b><br><br>
🔴 Event Venue<br>
🟢 Primary Diversion<br>
🔵 Secondary Diversion<br>
🔺 Avoid Route<br>
⚫ Police Station<br>
⭕ 500m Impact Radius
</div>
"""

m.get_root().html.add_child(folium.Element(legend))

# =====================================================
# DISPLAY
# =====================================================

st_folium(
    m,
    width=None,
    height=750,
    returned_objects=[]
)

# =====================================================
# DEPLOYMENT TABLE
# =====================================================

st.subheader("🚔 Police Deployment Summary")

st.dataframe(
    [
        {
            "Police Station": "Sadashivanagar PS",
            "Allocated Officers": 2,
            "Workload (%)": 80
        },
        {
            "Police Station": "Yeshwanthpura PS",
            "Allocated Officers": 3,
            "Workload (%)": 15
        }
    ],
    use_container_width=True
)
