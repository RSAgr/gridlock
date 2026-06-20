import pandas as pd
from geopy.distance import geodesic
from datetime import timedelta


def allocate_station_resources(
    junction_name,
    officers_required,
    start_time,
    duration_hours,
    mapping_file="junction_to_stations.csv",
    resources_file="police_station_resources.csv",
    deployments_file="police_deployments.csv"
):

    mapping_df = pd.read_csv(mapping_file)

    resources_df = pd.read_csv(resources_file)

    deployments_df = pd.read_csv(deployments_file)

    station_row = mapping_df[
        mapping_df["junction"] == junction_name
    ]

    if station_row.empty:
        return []

    primary_station = station_row.iloc[0]["responsible_station"]

    primary_row = resources_df[
        resources_df["station_name"]
        == primary_station
    ]

    if primary_row.empty:
        return []

    allocations = []

    remaining = officers_required

    start_time = pd.to_datetime(start_time)

    end_time = (
        start_time
        + timedelta(hours=duration_hours)
        + timedelta(hours=1)
    )

    # --------------------------
    # PRIMARY STATION
    # --------------------------

    total = primary_row.iloc[0]["total_officers"]

    available = primary_row.iloc[0]["available_officers"]

    used = total - available

    threshold = int(total * 0.8)

    capacity = max(
        threshold - used,
        0
    )

    allocated = min(
        remaining,
        capacity
    )

    if allocated > 0:

        resources_df.loc[
            resources_df["station_name"]
            == primary_station,
            "available_officers"
        ] -= allocated

        workload = round(
            (
                (
                    total
                    -
                    (
                        available - allocated
                    )
                )
                /
                total
            ) * 100,
            2
        )

        allocations.append({
            "station_name": primary_station,
            "officers_allocated": int(allocated),
            "workload_percent": workload
        })

        deployments_df.loc[
            len(deployments_df)
        ] = [
            primary_station,
            allocated,
            end_time
        ]

        remaining -= allocated

    # --------------------------
    # BACKUP STATIONS
    # --------------------------

    if remaining > 0:

        primary_lat = primary_row.iloc[0]["lat"]

        primary_lon = primary_row.iloc[0]["lon"]

        backup_df = resources_df[
            resources_df["station_name"]
            != primary_station
        ].copy()

        backup_df["distance"] = backup_df.apply(
            lambda row:
            geodesic(
                (primary_lat, primary_lon),
                (row["lat"], row["lon"])
            ).km,
            axis=1
        )

        backup_df = backup_df.sort_values(
            "distance"
        )

        for _, row in backup_df.iterrows():

            if remaining <= 0:
                break

            total = row["total_officers"]

            available = row["available_officers"]

            used = total - available

            threshold = int(total * 0.8)

            capacity = max(
                threshold - used,
                0
            )

            if capacity <= 0:
                continue

            allocated = min(
                remaining,
                capacity
            )

            resources_df.loc[
                resources_df["station_name"]
                == row["station_name"],
                "available_officers"
            ] -= allocated

            workload = round(
                (
                    (
                        total
                        -
                        (
                            available - allocated
                        )
                    )
                    /
                    total
                ) * 100,
                2
            )

            allocations.append({
                "station_name":
                    row["station_name"],

                "officers_allocated":
                    int(allocated),

                "workload_percent":
                    workload
            })

            deployments_df.loc[
                len(deployments_df)
            ] = [
                row["station_name"],
                allocated,
                end_time
            ]

            remaining -= allocated

    resources_df.to_csv(
        resources_file,
        index=False
    )

    deployments_df.to_csv(
        deployments_file,
        index=False
    )

    return allocations

def calculate_officers(
    junction_name,
    event_type,
    day_type,
    hour,
    start_time,
    junction_scores_df,
    junction_day_df,
    junction_hour_df,
    event_df
):

    # Base Junction Score

    junction_match = junction_scores_df[
    junction_scores_df["junction"] == junction_name
    ]

    if junction_match.empty:
        return 0

    base_score = junction_scores_df.loc[
        junction_scores_df["junction"] == junction_name,
        "risk_score"
    ].iloc[0]

    # Day Multiplier
    day_match = junction_day_df[
        (junction_day_df["junction"] == junction_name)
        &
        (junction_day_df["day_type"] == day_type)
    ]

    day_multiplier = (
        day_match.iloc[0]["day_multiplier"]
        if not day_match.empty
        else 1
    )

    # Hour Multiplier
    hour_match = junction_hour_df[
        (junction_hour_df["junction"] == junction_name)
        &
        (junction_hour_df["hour"] == hour)
    ]

    hour_multiplier = (
        hour_match.iloc[0]["hour_multiplier"]
        if not hour_match.empty
        else 1
    )

    # Event Score
    event_match = event_df[
        event_df["event_cause"].str.lower()
        == event_type.lower()
    ]

    event_score = (
        event_match.iloc[0]["event_congestion_score"]
        if not event_match.empty
        else 0
    )

    # Effective Junction Score
    effective_junction_score = (
        base_score *
        day_multiplier *
        hour_multiplier
    )

    # Deployment Score
    deployment_score = (
        0.6 * effective_junction_score +
        0.4 * event_score
    )

    officers = round(deployment_score / 8)

    allocation = allocate_station_resources(
        junction_name=junction_name,
        officers_required=officers,
        start_time=start_time,
        duration_hours=hour
    )

    return {
        "junction": junction_name,
        "officers_required": officers,
        "allocations": allocation
    }
    
###################### Dummy Way to Call ##############################
# result = calculate_officers(
#     junction_name="MekhriCircle",
#     event_type="accident",
#     day_type="Weekday",
#     hour=3,
#     start_time="2026-06-21 18:00:00",
#     junction_scores_df=junction_scores_df,
#     junction_day_df=junction_day_df,
#     junction_hour_df=junction_hour_df,
#     event_df=event_df
# )

# print(result)