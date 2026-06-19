import pandas as pd

OFFICER_SCALE = 8


def calculate_officers(
    junction_name,
    event_type,
    day_type,
    hour,
    junction_scores_df,
    junction_day_df,
    junction_hour_df,
    event_df
):

    # -----------------------------
    # Base Junction Score
    # -----------------------------
    junction_match = junction_scores_df[
        junction_scores_df["junction"] == junction_name
    ]

    if junction_match.empty:
        return {
            "base_score": 0,
            "day_multiplier": 1,
            "hour_multiplier": 1,
            "event_score": 0,
            "effective_junction_score": 0,
            "deployment_score": 0,
            "officers": 0
        }

    base_score = junction_match.iloc[0]["risk_score"]

    # -----------------------------
    # Day Multiplier
    # -----------------------------
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

    # -----------------------------
    # Hour Multiplier
    # -----------------------------
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

    # -----------------------------
    # Event Score
    # -----------------------------
    event_type = str(event_type).lower()

    event_match = event_df[
        event_df["event_cause"].str.lower()
        == event_type
    ]

    event_score = (
        event_match.iloc[0]["event_congestion_score"]
        if not event_match.empty
        else 0
    )

    # -----------------------------
    # Effective Junction Score
    # -----------------------------
    effective_junction_score = (
        base_score
        * day_multiplier
        * hour_multiplier
    )

    # -----------------------------
    # Deployment Score
    # -----------------------------
    deployment_score = (
        0.7 * effective_junction_score
        + 0.3 * event_score
    )

    # -----------------------------
    # Officers Required
    # -----------------------------
    officers = max(
        1,
        round(deployment_score / OFFICER_SCALE)
    )

    return {
        "base_score": round(base_score, 2),
        "day_multiplier": round(day_multiplier, 2),
        "hour_multiplier": round(hour_multiplier, 2),
        "event_score": round(event_score, 2),
        "effective_junction_score": round(effective_junction_score, 2),
        "deployment_score": round(deployment_score, 2),
        "officers": officers
    }