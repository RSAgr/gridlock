import streamlit as st
import folium
import json
from streamlit_folium import st_folium

from components.event_layer import add_event_layer
from components.junction_layer import add_junction_layer
from components.critical_zone_layer import add_critical_zone_layer
from components.deployment_layer import add_deployment_layer
from components.infrastructure_layer import add_infrastructure_layer
from components.diversion_layer import add_diversion_layer
from components.emergency_layer import add_emergency_layer

st.set_page_config(
    page_title="FlowGuard AI",
    page_icon="🚦",
    layout="wide"
)

st.markdown("""
<h1 style='margin-bottom:0px;'>
FlowGuard AI
</h1>
<p style='font-size:18px;color:#9CA3AF;margin-top:-8px;'>
Event-Aware Congestion Prediction & Resource Optimization
</p>
""", unsafe_allow_html=True)

st.divider()

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric("Active Events", "12")

with m2:
    st.metric("Critical Junctions", "8")

with m3:
    st.metric("Resources Deployed", "146")

with m4:
    st.metric("Diversions Active", "5")

st.divider()

st.subheader("Operations")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("### 📅 Plan Event")
        st.caption("Forecast congestion and pre-plan deployments.")
        if st.button(
            "Launch Planner",
            use_container_width=True,
            type="primary"
        ):
            st.switch_page("pages/1_Plan_Event.py")

with col2:
    with st.container(border=True):
        st.markdown("### 🚨 Report Incident")
        st.caption("Generate real-time response recommendations.")
        if st.button(
            "Open Incident Desk",
            use_container_width=True,
            type="primary"
        ):
            st.switch_page("pages/2_Report_Event.py")

st.divider()
with open("datasets/dummy.json") as f:
    data = json.load(f)

venue = data["event"]["venue"]

m = folium.Map(
    location=[venue["lat"], venue["lon"]],
    zoom_start=16
)

add_event_layer(m, data)
add_junction_layer(m, data)
add_critical_zone_layer(m, data)
add_deployment_layer(m, data)
add_infrastructure_layer(m, data)
add_diversion_layer(m, data)
add_emergency_layer(m, data)

st_folium(
    m,
    height=600,
    use_container_width=True
)

# st.subheader("Live City Overview")

# map_placeholder = """
# <div style="
# height:500px;
# border:1px solid rgba(255,255,255,0.1);
# border-radius:12px;
# display:flex;
# align-items:center;
# justify-content:center;
# background:rgba(255,255,255,0.02);
# font-size:20px;
# color:#9CA3AF;
# ">
# Interactive Congestion Map
# </div>
# """

# st.markdown(map_placeholder, unsafe_allow_html=True)

st.divider()

st.subheader("Recent Alerts")

with st.container(border=True):
    st.markdown("""
🔴 **MG Road Junction** — Severe congestion expected

🟠 **Queens Circle** — Diversion recommended

🟢 **Airport Corridor** — Operating normally
""")
    
st.divider()

st.subheader("Upcoming Events")

with st.container(border=True):
    st.markdown("""
1. Billi ards Championship — 2024-06-15, 18:00, City Sports Arena
2. Music Festival — 2024-06-20, 16:00, Central Park
""")
    
st.divider()

st.subheader("Live Events")

with st.container(border=True):
    st.markdown("""
1. Marathon — 2024-06-10, 07:00p.m. Downtown Streets
2. Sunny Music Concert — 2024-06-12, 19:00, Riverside Park
""")