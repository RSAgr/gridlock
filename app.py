import streamlit as st
import folium
from copy import deepcopy
from datetime import datetime
from streamlit_folium import st_folium

from components.event_layer import add_event_layer
from components.junction_layer import add_junction_layer
from components.critical_zone_layer import add_critical_zone_layer
from components.deployment_layer import add_deployment_layer
from components.infrastructure_layer import add_infrastructure_layer
from components.diversion_layer import add_diversion_layer
from components.emergency_layer import add_emergency_layer
from modules.routing_engine import RoutingEngine
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


def get_event_expected_officers(event, feedback_data):
    expected_officers = event.get("expected_officers", [])
    if isinstance(expected_officers, list):
        return [safe_int(value) for value in expected_officers]

    existing_officials = feedback_data.get("officials_by_junction", [])
    if not isinstance(existing_officials, list):
        return []

    return [
        safe_int(item.get("expected_officials"))
        for item in existing_officials
        if isinstance(item, dict)
    ]


def sync_feedback_widget_state(event_key, feedback_data, expected_officers):
    notes_key = f"feedback_notes_{event_key}"
    duration_key = f"actual_event_duration_{event_key}"

    if notes_key not in st.session_state:
        st.session_state[notes_key] = feedback_data.get("notes", "")

    if duration_key not in st.session_state:
        st.session_state[duration_key] = safe_int(
            feedback_data.get("actual_event_duration", 0)
        )

    for junction_index, officer_count in enumerate(expected_officers, start=1):
        officer_key = f"officials_{event_key}_{junction_index}"
        if officer_key not in st.session_state:
            st.session_state[officer_key] = safe_int(officer_count)


@st.cache_resource
def get_map_engine():
    return RoutingEngine("datasets/givenData.csv")


def build_node_lookup_maps(engine):
    node_details_by_id = {}
    node_details_by_label = {}

    for row in engine.unique_nodes.itertuples():
        label = (
            f"{row.junction.replace('_', ' ')}, "
            f"{row.corridor.replace('_', ' ')}, "
            f"{row.zone.replace('_', ' ')}"
        )
        details = {
            "node_id": row.node_id,
            "label": label,
            "lat": float(row.latitude),
            "lon": float(row.longitude),
        }
        node_details_by_id[str(row.node_id)] = details
        node_details_by_label[label] = details

    return node_details_by_id, node_details_by_label


def resolve_event_nodes(event, node_details_by_id, node_details_by_label):
    resolved_nodes = []
    seen = set()

    route_node_ids = event.get("route_node_ids", [])
    if isinstance(route_node_ids, list) and route_node_ids:
        for node_id in route_node_ids:
            details = node_details_by_id.get(str(node_id))
            if details and details["node_id"] not in seen:
                resolved_nodes.append(details)
                seen.add(details["node_id"])
        return resolved_nodes

    event_node_id = event.get("event_node_id")
    if event_node_id:
        details = node_details_by_id.get(str(event_node_id))
        if details:
            return [details]

    for label in get_event_junctions(event):
        details = node_details_by_label.get(str(label))
        if details and details["node_id"] not in seen:
            resolved_nodes.append(details)
            seen.add(details["node_id"])

    return resolved_nodes


def resolve_diversion_nodes(event, node_details_by_id):
    diversion_node_ids = event.get("diversion_route_node_ids", [])
    if not isinstance(diversion_node_ids, list):
        return []

    return [
        node_details_by_id[str(node_id)]
        for node_id in diversion_node_ids
        if str(node_id) in node_details_by_id
    ]


def pick_focus_event(event_records, node_details_by_id, node_details_by_label):
    sorted_events = sorted(
        event_records,
        key=lambda event: parse_event_datetime(event) or datetime.min,
        reverse=True
    )

    for status in ("live", "planned", "completed"):
        for event in sorted_events:
            if str(event.get("status", "")).lower() != status:
                continue

            resolved_nodes = resolve_event_nodes(
                event,
                node_details_by_id,
                node_details_by_label
            )
            if resolved_nodes:
                return event, resolved_nodes

    for event in sorted_events:
        resolved_nodes = resolve_event_nodes(
            event,
            node_details_by_id,
            node_details_by_label
        )
        if resolved_nodes:
            return event, resolved_nodes

    return None, []


def build_map_data(events_document, event_records, node_details_by_id, node_details_by_label):
    data = deepcopy(events_document) if isinstance(events_document, dict) else {}
    data["junctions"] = []
    data["diversions"] = []

    junctions_by_name = {}

    for event in event_records:
        resolved_nodes = resolve_event_nodes(
            event,
            node_details_by_id,
            node_details_by_label
        )
        if not resolved_nodes:
            continue

        divergence = is_truthy(event.get("divergence"))
        risk_score = float(
            event.get("ai_divergence_score")
            if event.get("ai_divergence_score") is not None
            else (80 if divergence else 40)
        )
        risk_level = "Critical" if divergence else "Moderate"

        for node in resolved_nodes:
            existing = junctions_by_name.get(node["label"])
            if existing:
                if risk_score > existing["risk_score"]:
                    existing["risk_score"] = risk_score
                    existing["risk_level"] = risk_level
                continue

            junctions_by_name[node["label"]] = {
                "name": node["label"],
                "lat": node["lat"],
                "lon": node["lon"],
                "risk_level": risk_level,
                "risk_score": risk_score,
            }

        diversion_nodes = resolve_diversion_nodes(event, node_details_by_id)
        if divergence and len(resolved_nodes) > 1 and len(diversion_nodes) > 1:
            data["diversions"].append({
                "blocked_route": [
                    [node["lat"], node["lon"]]
                    for node in resolved_nodes
                ],
                "alternate_route": [
                    [node["lat"], node["lon"]]
                    for node in diversion_nodes
                ]
            })

    data["junctions"] = list(junctions_by_name.values())

    focus_event, focus_nodes = pick_focus_event(
        event_records,
        node_details_by_id,
        node_details_by_label
    )
    if focus_event and focus_nodes:
        avg_lat = sum(node["lat"] for node in focus_nodes) / len(focus_nodes)
        avg_lon = sum(node["lon"] for node in focus_nodes) / len(focus_nodes)
        data["event"] = {
            "name": (
                focus_event.get("event_name")
                or str(focus_event.get("event_type", "Event")).replace("_", " ").title()
            ),
            "type": str(focus_event.get("event_type", "Event")).replace("_", " ").title(),
            "venue": {
                "name": focus_nodes[0]["label"],
                "lat": avg_lat,
                "lon": avg_lon,
            },
            "impact_radius": max(700, len(focus_nodes) * 350),
        }

    return data


events_document = load_events_document()
event_records = events_document.get("events", []) if isinstance(events_document, dict) else []
map_engine = get_map_engine()
node_details_by_id, node_details_by_label = build_node_lookup_maps(map_engine)
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

with st.container(border=True):
    st.markdown("### � Report Event")
    st.caption("Forecast congestion and pre-plan deployments.")
    if st.button(
        "Open Report",
        use_container_width=True,
        type="primary"
    ):
        st.switch_page("pages/1_Report_Event.py")

st.divider()
data = build_map_data(
    events_document,
    event_records,
    node_details_by_id,
    node_details_by_label
)

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
                feedback_data = event.get("feedback", {}) if isinstance(event.get("feedback"), dict) else {}
                has_saved_feedback = bool(feedback_data)
                popover_label = "Feedback Saved" if has_saved_feedback else "Feedback"

                with st.popover(popover_label, use_container_width=True):
                    st.caption("Capture a quick completion check-in.")

                    event_junctions = get_event_junctions(event)

                    st.markdown("**Actual officials deployed by junction**")
                    officials_by_junction = []
                    existing_expected_officers = get_event_expected_officers(
                        event,
                        feedback_data
                    )
                    sync_feedback_widget_state(
                        event_key,
                        feedback_data,
                        existing_expected_officers
                    )

                    submitted_at = feedback_data.get("submitted_at")
                    if submitted_at:
                        st.success(f"Saved on {submitted_at.replace('T', ' ')}")

                    if event_junctions:
                        for junction_index, junction_name in enumerate(event_junctions, start=1):

                            predicted_officers = None

                            deployment_prediction = event.get(
                                "deployment_prediction",
                                []
                            )

                            if isinstance(deployment_prediction, list):

                                route_junction = (
                                    junction_name.split(",")[0]
                                    .replace(" ", "")
                                )

                                for pred in deployment_prediction:

                                    pred_junction = str(
                                        pred.get("junction", "")
                                    ).replace(" ", "")

                                    if pred_junction == route_junction:

                                        predicted_officers = pred.get(
                                            "predicted_officers"
                                        )

                                        break

                            st.markdown(f"**{junction_name}**")

                            if predicted_officers is not None:
                                st.info(
                                    f"🤖 AI Predicted: {predicted_officers} officers"
                                )

                            actual_officers = st.number_input(
                                "Actual officers deployed",
                                min_value=0,
                                step=1,
                                value=st.session_state.get(
                                    f"officials_{event_key}_{junction_index}",
                                    (
                                        existing_expected_officers[junction_index - 1]
                                        if junction_index - 1 < len(existing_expected_officers)
                                        else 0
                                    )
                                ),
                                key=f"officials_{event_key}_{junction_index}"
                            )

                            officials_by_junction.append({
                                "junction": junction_name,
                                "expected_officials": actual_officers
                            })
                    else:
                        st.caption("No route or junction location found for this event.")

                    duration_key = f"actual_event_duration_{event_key}"
                    notes_key = f"feedback_notes_{event_key}"

                    actual_event_duration = st.number_input(
                        "Actual Event Duration (minutes)",
                        min_value=0,
                        step=1,
                        value=st.session_state.get(
                            duration_key,
                            safe_int(feedback_data.get("actual_event_duration", 0))
                        ),
                        key=duration_key
                    )

                    feedback_notes = st.text_area(
                        "Notes",
                        value=st.session_state.get(
                            notes_key,
                            feedback_data.get("notes", "")
                        ),
                        placeholder="What went well? What should improve?",
                        key=notes_key
                    )

                    if st.button(
                        "Update Feedback" if has_saved_feedback else "Save Feedback",
                        type="primary",
                        use_container_width=True,
                        key=f"save_feedback_{event_key}"
                    ):

                        prediction = event.get("deployment_prediction")
                        expected_officers = [
                            safe_int(item["expected_officials"])
                            for item in officials_by_junction
                        ]

                        if prediction and expected_officers:

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

                            feedback_for_learning = []

                            for pred in prediction:

                                actual_count = 0

                                pred_junction = str(
                                    pred["junction"]
                                ).replace(" ", "")

                                for actual in officials_by_junction:

                                    actual_junction = (
                                        str(actual["junction"])
                                        .split(",")[0]
                                        .replace(" ", "")
                                    )

                                    if actual_junction == pred_junction:

                                        actual_count = actual[
                                            "expected_officials"
                                        ]

                                        break

                                feedback_for_learning.append({
                                    "junction": pred["junction"],
                                    "predicted_officers": pred["predicted_officers"],
                                    "actual_officers": actual_count
                                })

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
                        event["expected_officers"] = expected_officers

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
