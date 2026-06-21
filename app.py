import streamlit as st
import folium
from datetime import datetime
from streamlit_folium import st_folium

from components.event_layer import add_event_layer
from components.junction_layer import add_junction_layer
from components.critical_zone_layer import add_critical_zone_layer
from components.deployment_layer import add_deployment_layer
from components.infrastructure_layer import add_infrastructure_layer
from components.diversion_layer import add_diversion_layer
from components.emergency_layer import add_emergency_layer
from modules.events_store import load_events_document, save_event_records
from modules.self_learning import self_learn
import pandas as pd

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


def safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def is_truthy(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def parse_event_datetime(event):
    event_date = event.get("event_date")
    if not event_date:
        return None

    event_time = event.get("event_time") or "00:00:00"

    try:
        return datetime.fromisoformat(f"{event_date}T{event_time}")
    except ValueError:
        return None


def event_has_started(event):
    event_dt = parse_event_datetime(event)
    return bool(event_dt and event_dt <= datetime.now())


def save_events_to_disk(event_list):
    save_event_records(event_list)


def get_event_key(event, fallback_index):
    return str(event.get("id") or event.get("event_id") or fallback_index)


def format_event_entry(event):
    title = event.get("event_name") or str(event.get("event_type", "Untitled Event")).replace("_", " ").title()
    details = []

    event_dt = parse_event_datetime(event)
    if event_dt:
        details.append(event_dt.strftime("%Y-%m-%d, %H:%M"))
    elif event.get("event_date"):
        details.append(event["event_date"])

    if event.get("event_location"):
        details.append(event["event_location"])
    elif event.get("event_type"):
        details.append(str(event["event_type"]).replace("_", " ").title())

    return f"{title} — {', '.join(details)}" if details else title


def get_event_junctions(event):
    route = event.get("route")

    if isinstance(route, list) and route:
        return [str(junction) for junction in route if junction]

    event_location = event.get("event_location")
    if event_location:
        return [str(event_location)]

    return []


events_document = load_events_document()
event_records = events_document.get("events", []) if isinstance(events_document, dict) else []
scheduled_events = [event for event in event_records if event.get("event_date")]
upcoming_events = [event for event in scheduled_events if str(event.get("status", "")).lower() == "planned"]
if not upcoming_events:
    upcoming_events = scheduled_events

live_events = [event for event in event_records if str(event.get("status", "")).lower() == "live"]
if not live_events:
    live_events = [event for event in event_records if not event.get("event_date")]

recent_completed_events = [
    event for event in event_records if event_has_started(event)
]
recent_completed_events = sorted(
    recent_completed_events,
    key=lambda event: parse_event_datetime(event) or datetime.min,
    reverse=True
)[:5]

active_events_count = len(event_records)
critical_junctions_count = len({event.get("event_location") for event in event_records if event.get("event_location")})
resources_deployed = sum(safe_int(event.get("attendance")) for event in event_records)
diversions_active = sum(1 for event in event_records if is_truthy(event.get("divergence")) and event_has_started(event))

st.divider()

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric("Active Events", active_events_count)

with m2:
    st.metric("Critical Junctions", critical_junctions_count)

with m3:
    st.metric("Resources Deployed", resources_deployed)

with m4:
    st.metric("Diversions Active", diversions_active)

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
data = events_document if isinstance(events_document, dict) else {}

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
    if upcoming_events:
        st.markdown("\n".join(f"{index}. {format_event_entry(event)}" for index, event in enumerate(upcoming_events, start=1)))
    else:
        st.caption("No upcoming events found in events.json.")
    
st.divider()

st.subheader("Live Events")

with st.container(border=True):
    if live_events:
        st.markdown("\n".join(f"{index}. {format_event_entry(event)}" for index, event in enumerate(live_events, start=1)))
    else:
        st.caption("No live events found in events.json.")

st.divider()

st.subheader("Recent Completed Events")

with st.container(border=True):
    if recent_completed_events:
        for index, event in enumerate(recent_completed_events, start=1):
            row_left, row_right = st.columns([5, 1])

            with row_left:
                st.markdown(f"**{index}. {format_event_entry(event)}**")
                if event.get("status"):
                    st.caption(f"Status: {event['status']}")

            with row_right:
                event_key = get_event_key(event, index)
                with st.popover("Feedback", use_container_width=True):
                    st.caption("Capture a quick completion check-in.")

                    feedback_data = event.get("feedback", {}) if isinstance(event.get("feedback"), dict) else {}
                    event_junctions = get_event_junctions(event)

                    st.markdown("**Actual officials deployed by junction**")
                    officials_by_junction = []

                    if event_junctions:
                        existing_officials = feedback_data.get("officials_by_junction", [])
                        existing_officials_map = {}

                        if isinstance(existing_officials, list):
                            for item in existing_officials:
                                if isinstance(item, dict) and item.get("junction"):
                                    existing_officials_map[str(item["junction"])] = safe_int(item.get("expected_officials"))

                        for junction_index, junction_name in enumerate(event_junctions, start=1):

                            predicted_officers = None

                            deployment_prediction = event.get(
                                "deployment_prediction",
                                {}
                            )

                            if (
                                deployment_prediction
                                and deployment_prediction.get("junction")
                            ):
                                predicted_officers = deployment_prediction.get(
                                    "predicted_officers"
                                )

                            st.markdown(f"**{junction_name}**")

                            if predicted_officers is not None:
                                st.info(
                                    f"🤖 AI Predicted: {predicted_officers} officers"
                                )

                            actual_officers = st.number_input(
                                "Actual officers deployed",
                                min_value=0,
                                step=1,
                                value=existing_officials_map.get(
                                    junction_name,
                                    0
                                ),
                                key=f"officials_{event_key}_{junction_index}"
                            )

                            officials_by_junction.append({
                                "junction": junction_name,
                                "expected_officials": actual_officers
                            })
                    else:
                        st.caption("No route or junction location found for this event.")

                    actual_event_duration = st.number_input(
                        "Actual Event Duration (minutes)",
                        min_value=0,
                        step=1,
                        value=safe_int(feedback_data.get("actual_event_duration", 0)),
                        key=f"actual_event_duration_{event_key}"
                    )

                    feedback_notes = st.text_area(
                        "Notes",
                        value=feedback_data.get("notes", ""),
                        placeholder="What went well? What should improve?",
                        key=f"feedback_notes_{event_key}"
                    )

                    if st.button(
                        "Save Feedback",
                        type="primary",
                        use_container_width=True,
                        key=f"save_feedback_{event_key}"
                    ):

                        prediction = event.get("deployment_prediction")

                        if prediction:

                            junction_df = pd.read_csv(
                                "datasets/junction_scores.csv"
                            )

                            junction_day_df = pd.read_csv(
                                "datasets/junction_daytype_multipliers.csv"
                            )

                            junction_hour_df = pd.read_csv(
                                "datasets/junction_hour_multipliers.csv"
                            )

                            event_df = pd.read_csv(
                                "datasets/event_congestion_scores.csv"
                            )

                            feedback_for_learning = [
                                {
                                    "junction": prediction["junction"],
                                    "predicted_officers": prediction["predicted_officers"],
                                    "actual_officers": officials_by_junction[0]["expected_officials"]
                                }
                            ]

                            (
                                junction_df,
                                junction_day_df,
                                junction_hour_df,
                                event_df
                            ) = self_learn(
                                feedback_data=feedback_for_learning,
                                event_type=event["event_type"],
                                day_type=(
                                    "Weekend"
                                    if pd.to_datetime(event["event_date"]).dayofweek >= 5
                                    else "Weekday"
                                ),
                                hour=pd.to_datetime(event["event_time"]).hour,
                                junction_df=junction_df,
                                junction_day_df=junction_day_df,
                                junction_hour_df=junction_hour_df,
                                event_df=event_df
                            )

                            junction_df.to_csv(
                                "datasets/junction_scores.csv",
                                index=False
                            )

                            junction_day_df.to_csv(
                                "datasets/junction_daytype_multipliers.csv",
                                index=False
                            )

                            junction_hour_df.to_csv(
                                "datasets/junction_hour_multipliers.csv",
                                index=False
                            )

                            event_df.to_csv(
                                "datasets/event_congestion_scores.csv",
                                index=False
                            )

                        event["status"] = "completed"

                        event["feedback"] = {
                            "officials_by_junction": officials_by_junction,
                            "actual_event_duration": actual_event_duration,
                            "notes": feedback_notes,
                            "submitted_at": datetime.now().isoformat(timespec="seconds")
                        }

                        save_events_to_disk(event_records)

                        st.success("Feedback saved.")
                        st.rerun()

                        if prediction:

                            junction_df = pd.read_csv(
                                "datasets/junction_scores.csv"
                            )

                            junction_day_df = pd.read_csv(
                                "datasets/junction_daytype_multipliers.csv"
                            )

                            junction_hour_df = pd.read_csv(
                                "datasets/junction_hour_multipliers.csv"
                            )

                            event_df = pd.read_csv(
                                "datasets/event_congestion_scores.csv"
                            )                   
    else:
        st.caption("No recent completed events found in events.json yet.")