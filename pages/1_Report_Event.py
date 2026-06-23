import streamlit as st
from datetime import date
import pandas as pd
from datetime import datetime

from modules.routing_engine import RoutingEngine
from modules.divergence_scorer import calculate_divergence_requirement
from modules.calculate_officers import calculate_officers
from modules.refresh_officer_count import refresh_officer_availability
from modules.events_store import (append_event,load_events_document,save_event_records)
from modules.calculate_officers import calculate_officers
from datetime import timedelta

st.set_page_config(page_title="Plan Event", page_icon="📅", layout="wide")

# Cache the engine
@st.cache_resource
def get_engine():
    return RoutingEngine("datasets/givenData.csv")

# Cache the scoring CSVs
@st.cache_data
def load_scoring_data():
    e_scores = pd.read_csv(
        "datasets/event_congestion_scores.csv"
    )

    j_scores = pd.read_csv(
        "datasets/junction_scores.csv"
    )

    junction_day_df = pd.read_csv(
        "datasets/junction_daytype_multipliers.csv"
    )

    junction_hour_df = pd.read_csv(
        "datasets/junction_hour_multipliers.csv"
    )

    return (
        e_scores,
        j_scores,
        junction_day_df,
        junction_hour_df
    )

engine = get_engine()

(
    e_scores,
    j_scores,
    junction_day_df,
    junction_hour_df
) = load_scoring_data()

def save_event(event_data):
    append_event(event_data)


def build_event_end_time(event_date, event_time, minimum_minutes=5):
    return datetime.combine(event_date, event_time) + timedelta(minutes=minimum_minutes)


def update_saved_event(event_id, updates):
    events_doc = load_events_document()
    events = events_doc["events"]

    for event in events:
        if str(event.get("id")) == str(event_id):
            event.update(updates)
            save_event_records(events)
            return

all_nodes_dict = engine.get_all_nodes_dict()

st.title("📅 Event Planner")
st.caption("Create a planned event and generate congestion forecasts.")
st.divider()

event_types = [
    "debris", "water_logging", "vehicle_breakdown", "tree_fall",
    "congestion", "pot_holes", "construction", "road_conditions", 
    "accident", "test_demo", "protest", "procession", 
    "public_event", "vip_movement", "political_rally", "festival", "marathon", "sports_event", "others"
]

route_based_events = {
    "vip_movement", "political_rally", "festival", "marathon", 
    "sports_event", "procession", "protest"
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

    if 'route_path' not in st.session_state:
        st.session_state.route_path = []

    r_col1, r_col2 = st.columns([2, 1])
    with r_col1:
        if len(st.session_state.route_path) == 0:
            start_node = st.selectbox("🏁 Select Starting Point:", options=list(all_nodes_dict.keys()), format_func=lambda x: all_nodes_dict[x], key="route_start")
            if st.button("Set Start Point"):
                st.session_state.route_path.append(start_node)
                st.rerun()
        else:
            current_tail_node = st.session_state.route_path[-1]
            valid_neighbors = engine.get_neighbors_dict(current_tail_node)
            if len(valid_neighbors) > 0:
                next_node = st.selectbox("📍 Select Next Connected Intersection:", options=list(valid_neighbors.keys()), format_func=lambda x: valid_neighbors[x], key=f"next_node_{len(st.session_state.route_path)}")
                if st.button("➕ Add to Route"):
                    st.session_state.route_path.append(next_node)
                    st.rerun()
            else:
                st.error("🛑 Dead End: No historical outgoing paths exist from this junction in the dataset.")

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
    save_col, diversion_col = st.columns(2)

    with save_col:
        if st.button("💾 Save Event", use_container_width=True):
            event_id = datetime.now().strftime("%Y%m%d%H%M%S%f")

            payload = {
                "id": event_id,
                "event_type": event_type,
                "event_date": str(event_date),
                "event_time": str(event_time),
                "estimated_end_time": build_event_end_time(event_date, event_time).isoformat(timespec="seconds"),
                "attendance": expected_attendance,
                "route": [all_nodes_dict[n] for n in st.session_state.route_path],
                "route_node_ids": st.session_state.route_path,
                "status": "planned",
                "divergence": False
            }

            save_event(payload)
            st.success("✅ Event saved successfully.")

    with diversion_col:
        if st.button("🚧 Generate Diversion Plan", type="primary", use_container_width=True):
            refresh_officer_availability(current_time=f"{event_date} {event_time}")
            if len(st.session_state.route_path) > 1:
                event_id = datetime.now().strftime("%Y%m%d%H%M%S%f")

                payload = {
                    "id": event_id,
                    "event_type": event_type,
                    "event_date": str(event_date),
                    "event_time": str(event_time),
                    "estimated_end_time": build_event_end_time(event_date, event_time).isoformat(timespec="seconds"),
                    "attendance": expected_attendance,
                    "route": [all_nodes_dict[n] for n in st.session_state.route_path],
                    "route_node_ids": st.session_state.route_path,
                    "status": "planned",
                    "divergence": True
                }

                save_event(payload)
                st.session_state["route_event_id"] = event_id

                st.subheader(
                    "🤖 FlowGuard AI Route Detour Generation"
                )

                with st.spinner(
                    "Traversing city adjacency graph to compute bypass corridor..."
                ):

                    is_wknd = (
                        pd.to_datetime(event_date).dayofweek >= 5
                    )

                    hr_val = event_time.hour
                    detour = engine.get_route_diversions(st.session_state.route_path, hr_val, is_wknd, active_event_type=event_type)
                    
                    if detour['status'] == 'success':
                        diversion_junctions = [
                                node["junction"].replace(" ", "")
                                for node in detour["path"]
                            ]
                        update_saved_event(
                            event_id,
                            {
                                "diversion_route_node_ids": detour.get("node_ids", []),
                                "diversion_route": [
                                    f"{step['junction']}, {step['corridor']}"
                                    for step in detour["path"]
                                ]
                            }
                        )
                        st.session_state["diversion_junctions"] = diversion_junctions
                        st.session_state["detour_generated"] = True
                        st.session_state["event_type"] = event_type
                        st.session_state["hour"] = hr_val
                        st.session_state["start_time"] = f"{event_date} {event_time}"
                        st.session_state["day_type"] = "Weekend" if is_wknd else "Weekday"
                        st.success(f"✅ **Continuous Bypass Route Secured!** (Avg Path Health: {detour['avg_health']:.2f})")
                        with st.container(border=True):
                            st.markdown("### 🗺️ Recommended Bypass Stream")
                            for idx, step in enumerate(detour['path']):
                                if idx == 0: st.write(f"🏁 **Divert From:** {step['junction']} ({step['corridor']})")
                                elif idx == len(detour['path']) - 1: st.write(f"🏁 **Rejoin At:** {step['junction']} ({step['corridor']})")
                                else: st.write(f" ↪️ **Detour Via:** {step['junction']} *(Health: {step['health']:.2f})*")
                        st.divider()

                    else:
                        st.warning(
                            "⚠️ Graph Disconnect."
                        )

                with st.expander("⚙️ View JSON Payload"):
                    st.json(payload)
            else:
                 st.warning(
                    "You must build an active segment matrix "
                    "(at least 2 nodes) before evaluating "
                    "pipeline deployment."
                )
                
            
    if st.session_state.get("detour_generated", False):

        if st.button(
            "👮 Generate Deployment Plan",
            use_container_width=True,
            key="route_deployment"
        ):
            st.session_state["show_route_deployment"] = True

    if st.session_state.get("show_route_deployment", False):

        st.subheader("👮 Police Deployment Plan")

        deployment_predictions = []

        for junction in st.session_state["diversion_junctions"]:

            result = calculate_officers(
                junction_name=junction,
                event_type=st.session_state["event_type"],
                day_type=st.session_state["day_type"],
                hour=st.session_state["hour"],
                start_time=st.session_state["start_time"]
            )
            deployment_predictions.append({
                "junction": result["junction"],
                "predicted_officers": result["officers_required"],
                "actual_officers": None
            })

            with st.container(border=True):

                st.markdown(
                    f"### 🚦 {result['junction']}"
                )

                st.write(
                    f"Required Officers: {result['officers_required']}"
                )

                for alloc in result["allocations"]:

                    st.success(
                        f"🚔 {alloc['station_name']} → "
                        f"{alloc['officers_allocated']} officers "
                        f"(Workload: {alloc['workload_percent']}%)"
                    )
        events_doc = load_events_document()
        events = events_doc["events"]
        route_event_id = st.session_state.get("route_event_id")

        for event in reversed(events):
            if route_event_id and str(event.get("id")) != str(route_event_id):
                continue

            if (
                event.get("event_type")
                == st.session_state["event_type"]
                and "route" in event
                and "deployment_prediction" not in event
            ):
                event["deployment_prediction"] = deployment_predictions
                break

        save_event_records(events)
            

else:
    # --- SINGLE POINT EVENT ---
    st.subheader("Event Location")
    event_location = st.selectbox("Search & Select Event Location:", options=list(all_nodes_dict.keys()), format_func=lambda x: all_nodes_dict[x])

    # ==========================================
    # NEW: AI DIVERGENCE SCORE UNIT
    # ==========================================
    st.divider()
    st.markdown("###  AI Divergence Assessment")
    
    # Extract clean junction name for the scorer
    raw_junction_name = engine.node_lookup[event_location]['junction'].replace('_', '')
    
    div_assessment = calculate_divergence_requirement(
        junction_name=raw_junction_name,
        event_type=event_type,
        attendance=expected_attendance,
        j_scores_df=j_scores,
        e_scores_df=e_scores
    )

    # Display the visual recommendation based on the score
    d_col1, d_col2 = st.columns([3, 1])
    with d_col1:
        if div_assessment['requires_divergence']:
            st.error(f"⚠️ **Divergence Recommended:** The severity of this event exceeds local traffic thresholds.")
        else:
            st.success(f"✅ **Divergence NOT Required:** Impact is minor. Traffic can likely be managed on-site.")
    with d_col2:
        st.metric("Divergence Risk Score", f"{div_assessment['score']} / 100")
    
    st.write("") # Spacer

    save_col, diversion_col = st.columns(2)

    with save_col:
        if st.button("💾 Save Event", use_container_width=True):
            event_id = datetime.now().strftime("%Y%m%d%H%M%S%f")

            day_type = (
                "Weekend"
                if pd.to_datetime(event_date).dayofweek >= 5
                else "Weekday"
            )

            prediction = calculate_officers(
                junction_name=raw_junction_name,
                event_type=event_type,
                day_type=day_type,
                hour=event_time.hour,
                start_time=f"{event_date} {event_time}",
                junction_scores_df=j_scores,
                junction_day_df=junction_day_df,
                junction_hour_df=junction_hour_df,
                event_df=e_scores
            )
            deployment_prediction = [
                {
                    "junction": prediction["junction"],
                    "predicted_officers": prediction["officers_required"],
                    "actual_officers": None
                }
            ]

            payload = {
                "id": event_id,
                "event_type": event_type,
                "event_date": str(event_date),
                "event_time": str(event_time),
                "estimated_end_time": build_event_end_time(event_date, event_time).isoformat(timespec="seconds"),
                "attendance": expected_attendance,
                "event_node_id": event_location,
                "event_location": all_nodes_dict[event_location],
                "status": "planned",
                "divergence": bool(div_assessment['requires_divergence']),
                "deployment_prediction": deployment_prediction
            }

            save_event(payload)

            st.success(
    f"""
✅ Event saved successfully

🤖 AI Predicted Officers: {prediction['officers_required']}

📈 Future predictions will improve through post-event feedback.
"""
)
            
    # with save_col:
    #     if st.button("💾 Save Event", use_container_width=True):
    #         payload = {
    #             "id": datetime.now().strftime("%Y%m%d%H%M%S"),
    #             "event_type": event_type,
    #             "event_date": str(event_date),
    #             "event_time": str(event_time),
    #             "attendance": expected_attendance,
    #             "event_location": all_nodes_dict[event_location],
    #             "status": "planned",
    #             "divergence": bool(div_assessment['requires_divergence'])
    #         }
    #         save_event(payload)
    #         st.success("✅ Event saved successfully.")

    with diversion_col:
        if st.button("🚧 Generate Diversion Plan", type="primary", use_container_width=True):
            refresh_officer_availability(current_time=f"{event_date} {event_time}")
            event_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
            day_type = (
                "Weekend"
                if pd.to_datetime(event_date).dayofweek >= 5
                else "Weekday"
            )

            prediction = calculate_officers(
                junction_name=raw_junction_name,
                event_type=event_type,
                day_type=day_type,
                hour=event_time.hour,
                start_time=f"{event_date} {event_time}"
            )

            deployment_prediction = [
                {
                    "junction": prediction["junction"],
                    "predicted_officers": prediction["officers_required"],
                    "actual_officers": None
                }
            ]
            payload = {
                "id": event_id,
                "event_type": event_type,
                "event_date": str(event_date),
                "event_time": str(event_time),
                "estimated_end_time": build_event_end_time(event_date, event_time).isoformat(timespec="seconds"),
                "attendance": expected_attendance,
                "event_node_id": event_location,
                "event_location": all_nodes_dict[event_location],
                "status": "planned",
                "ai_divergence_score": div_assessment['score'],
                "divergence": bool(div_assessment['requires_divergence']),
                "deployment_prediction": deployment_prediction
            }
            save_event(payload)
            
            st.subheader("🤖 FlowGuard AI Recommendations")
            
            # Gating Logic: Only run heavy routing if AI says yes (or show a warning but run it anyway)
            if not div_assessment['requires_divergence']:
                st.info("🚦 Note: AI indicated divergence was not strictly necessary, but generating optimal detours anyway as requested.")

            with st.spinner("Calculating spatial diversions..."):
                is_wknd = pd.to_datetime(event_date).dayofweek >= 5
                hr_val = event_time.hour
                recs = engine.get_single_point_diversions(event_location, hr_val, is_wknd)
                
                with st.container(border=True):
                    if len(recs) >= 2:
                        best_1 = recs.iloc[0]['junction'].replace('_', ' ')
                        best_2 = recs.iloc[1]['junction'].replace('_', ' ')
                        worst = recs.iloc[-1]['junction'].replace('_', ' ')
                        st.success(f"🟢 **Primary Detour:** Route via **{best_1}** (Health Score: {recs.iloc[0]['health']:.2f})")
                        st.success(f"🔵 **Secondary Detour:** Route via **{best_2}** (Health Score: {recs.iloc[1]['health']:.2f})")
                        st.error(f"🔴 **Avoid:** Do not route via **{worst}** (Health Score: {recs.iloc[-1]['health']:.2f})")
                    elif len(recs) == 1:
                        st.info(f"✅ **Single Detour:** Route via **{recs.iloc[0]['junction'].replace('_', ' ')}**")
                    else:
                        st.warning("No alternative routes found within the spatial constraints.")

            suggested_diversion_node_ids = (
                recs["node_id"].head(2).tolist()
                if len(recs) > 0 and "node_id" in recs.columns
                else []
            )
            update_saved_event(
                event_id,
                {
                    "suggested_diversion_node_ids": suggested_diversion_node_ids,
                    "diversion_route_node_ids": suggested_diversion_node_ids,
                }
            )

            st.success("Stationary Event processed successfully.")
            st.session_state["single_point_ready"] = True
            st.session_state["single_junction"] = raw_junction_name
            st.session_state["single_event_type"] = event_type
            st.session_state["single_day_type"] = "Weekend" if is_wknd else "Weekday"
            st.session_state["single_hour"] = hr_val
            st.session_state["single_start_time"] = f"{event_date} {event_time}"
            st.divider()

            
                        
            with st.expander("⚙️ View JSON Payload"):
                st.json(payload)
    
    if st.session_state.get("single_point_ready", False):

        if st.button(
            "👮 Generate Deployment Plan",
            use_container_width=True,
            key="single_point_deployment"
        ):
            st.session_state["show_single_deployment"] = True

    if st.session_state.get("show_single_deployment", False):

        try:
            result = calculate_officers(
                junction_name=st.session_state["single_junction"],
                event_type=st.session_state["single_event_type"],
                day_type=st.session_state["single_day_type"],
                hour=st.session_state["single_hour"],
                start_time=st.session_state["single_start_time"]
            )

            st.subheader("👮 Police Deployment Plan")

            with st.container(border=True):

                st.markdown(
                    f"### 🚦 {result['junction']}"
                )

                st.write(
                    f"Required Officers: {result['officers_required']}"
                )

                for alloc in result["allocations"]:

                    st.success(
                        f"🚔 {alloc['station_name']} → "
                        f"{alloc['officers_allocated']} officers "
                        f"(Workload: {alloc['workload_percent']}%)"
                    )

        except Exception as e:
            st.error(str(e))
                
