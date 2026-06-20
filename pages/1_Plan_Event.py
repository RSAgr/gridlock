import streamlit as st
from datetime import date
import pandas as pd

# Import the custom engine
from modules.routing_engine import RoutingEngine

st.set_page_config(
    page_title="Plan Event",
    page_icon="📅",
    layout="wide"
)

# Cache the engine so it only computes the map topology once
@st.cache_resource
def get_engine():
    return RoutingEngine("datasets/givenData.csv")

engine = get_engine()
all_nodes_dict = engine.get_all_nodes_dict()

st.title("📅 Event Planner")
st.caption("Create a planned event and generate congestion forecasts.")
st.divider()

# Unify the event types so the if-statement triggers correctly
event_types = [
    "debris", "water_logging", "vehicle_breakdown", "tree_fall",
    "congestion", "pot_holes", "construction", "road_conditions", 
    "accident", "test_demo", "protest", "procession", 
    "public_event", "vip_movement", "political_rally", "festival", "marathon", "sports_event", "others"
]

route_based_events = {
    "vip_movement",
    "political_rally",
    "festival",
    "marathon",
    "sports_event",
    "procession",
    "protest"
}

# --- 1. EVENT PARAMETERS ---
col1, col2 = st.columns(2)
with col1:
    event_type = st.selectbox("Event Type", event_types)
with col2:
    expected_attendance = st.number_input("Expected Attendance", min_value=0, step=100)

col1, col2 = st.columns(2)
with col1:
    event_date = st.date_input("Event Date", value=date.today())
with col2:
    event_time = st.time_input("Start Time")

st.divider()

# --- 2. DYNAMIC LOCATION / ROUTE BUILDER ---
if event_type in route_based_events:
    
    st.subheader("Route Information")
    st.info("Build a connected route. Options strictly filter to valid adjacent intersections based on historical traffic flow.")

    # Initialize session state array to hold the user's route
    if 'route_path' not in st.session_state:
        st.session_state.route_path = []

    r_col1, r_col2 = st.columns([2, 1])
    
    with r_col1:
        # If the path is empty, allow them to pick ANY node to start
        if len(st.session_state.route_path) == 0:
            start_node = st.selectbox(
                "🏁 Select Starting Point:",
                options=list(all_nodes_dict.keys()),
                format_func=lambda x: all_nodes_dict[x],
                key="route_start"
            )
            if st.button("Set Start Point"):
                st.session_state.route_path.append(start_node)
                st.rerun()
                
        # If path has started, show ONLY downstream neighbors
        else:
            current_tail_node = st.session_state.route_path[-1]
            valid_neighbors = engine.get_neighbors_dict(current_tail_node)
            
            if len(valid_neighbors) > 0:
                next_node = st.selectbox(
                    "📍 Select Next Connected Intersection:",
                    options=list(valid_neighbors.keys()),
                    format_func=lambda x: valid_neighbors[x],
                    key=f"next_node_{len(st.session_state.route_path)}"
                )
                if st.button("➕ Add to Route"):
                    st.session_state.route_path.append(next_node)
                    st.rerun()
            else:
                st.error("🛑 Dead End: No historical outgoing paths exist from this junction in the dataset.")

    # Show the active built route
    with r_col2:
        with st.container(border=True):
            st.markdown("### 🗺️ Planned Route")
            if len(st.session_state.route_path) == 0:
                st.caption("Route is empty. Select a starting point.")
            else:
                for idx, n_id in enumerate(st.session_state.route_path):
                    st.markdown(f"**{idx + 1}.** {all_nodes_dict[n_id]}")
                
                st.divider()
                if st.button("🗑️ Clear Route", use_container_width=True):
                    st.session_state.route_path = []
                    st.rerun()

    st.divider()
    if st.button("🚀 Process Dynamic Route Map", type="primary", use_container_width=True):
        if len(st.session_state.route_path) > 1:
            st.subheader("🤖 FlowGuard AI Route Detour Generation")
            
            with st.spinner("Traversing city adjacency graph to compute bypass corridor..."):
                is_wknd = pd.to_datetime(event_date).dayofweek >= 5
                hr_val = event_time.hour
                
                # Call the new BFS Routing Engine
                detour = engine.get_route_diversions(st.session_state.route_path, hr_val, is_wknd)
                
                if detour['status'] == 'success':
                    st.success(f"✅ **Continuous Bypass Route Secured!** (Avg Path Health: {detour['avg_health']:.2f})")
                    
                    with st.container(border=True):
                        st.markdown("### 🗺️ Recommended Bypass Stream")
                        for idx, step in enumerate(detour['path']):
                            if idx == 0:
                                st.write(f"🏁 **Divert From:** {step['junction']} ({step['corridor']})")
                            elif idx == len(detour['path']) - 1:
                                st.write(f"🏁 **Rejoin At:** {step['junction']} ({step['corridor']})")
                            else:
                                st.write(f" ↪️ **Detour Via:** {step['junction']} *(Health: {step['health']:.2f})*")
                else:
                    st.warning("⚠️ **Graph Disconnect:** Could not find a continuous alternate path avoiding the blocked zone in the historical dataset.")
                    st.info("Here are the clearest standalone fallback junctions near the origin:")
                    for idx, row in detour['nodes'].iterrows():
                         st.write(f"👉 **{row['junction'].replace('_', ' ')}** *(Score: {row['health']:.2f})*")
                         
            # JSON Payload Submission
            payload = {
                "event_type": event_type,
                "event_date": str(event_date),
                "event_time": str(event_time),
                "attendance_matrix": expected_attendance,
                "vector_trail": [all_nodes_dict[n] for n in st.session_state.route_path]
            }
            with st.expander("⚙️ View JSON Payload"):
                st.json(payload)
        else:
            st.warning("You must build an active segment matrix (at least 2 nodes) before evaluating pipeline deployment.")

else:
    # --- SINGLE POINT EVENT ---
    st.subheader("Event Location")
    
    event_location = st.selectbox(
        "Search & Select Event Location:",
        options=list(all_nodes_dict.keys()),
        format_func=lambda x: all_nodes_dict[x]
    )

    st.divider()
    
    if st.button("Generate Deployment Plan", type="primary", use_container_width=True):
        
        st.subheader(" FlowGuard AI Recommendations")
        with st.spinner("Calculating spatial diversions..."):
            is_wknd = pd.to_datetime(event_date).dayofweek >= 5
            hr_val = event_time.hour
            
            # Run Health Score Logic
            recs = engine.get_single_point_diversions(event_location, hr_val, is_wknd)
            
            with st.container(border=True):
                if len(recs) >= 2:
                    best_1 = recs.iloc[0]['junction'].replace('_', ' ')
                    best_2 = recs.iloc[1]['junction'].replace('_', ' ')
                    worst = recs.iloc[-1]['junction'].replace('_', ' ')
                    st.success(f" **Primary Detour:** Route via **{best_1}** (Health Score: {recs.iloc[0]['health']:.2f})")
                    st.success(f" **Secondary Detour:** Route via **{best_2}** (Health Score: {recs.iloc[1]['health']:.2f})")
                    st.error(f" **Avoid:** Do not route via **{worst}** (Health Score: {recs.iloc[-1]['health']:.2f})")
                elif len(recs) == 1:
                    st.info(f" **Single Detour:** Route via **{recs.iloc[0]['junction'].replace('_', ' ')}**")
                else:
                    st.warning("No alternative routes found within the spatial constraints.")

        # Display final JSON payload 
        payload = {
            "event_type": event_type,
            "event_date": str(event_date),
            "event_time": str(event_time),
            "attendance": expected_attendance,
            "event_location": all_nodes_dict[event_location]
        }
        st.success("Stationary Event submitted successfully.")
        with st.expander("⚙️ View JSON Payload"):
            st.json(payload)