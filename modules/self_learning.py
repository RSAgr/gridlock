def self_learn(
    feedback_data,
    event_type,
    day_type,
    hour,
    junction_df,
    junction_day_df,
    junction_hour_df,
    event_df,
    lr=0.15
):

    total_predicted = 0
    total_actual = 0

    for item in feedback_data:

        junction_name = item["junction"]
        predicted = max(item["predicted_officers"], 1)
        actual = item["actual_officers"]

        total_predicted += predicted
        total_actual += actual

        feedback_ratio = actual / predicted
        error = feedback_ratio - 1

        # Junction block contributes 50%
        correction = (
            1 + lr * error * 0.5
        )

        # =====================================
        # FIND OR CREATE JUNCTION
        # =====================================

        junction_match = junction_df[
            junction_df["junction"]
            .astype(str)
            .str.lower()
            ==
            junction_name.lower()
        ]

        if junction_match.empty:

            median_risk = junction_df["risk_score"].median()

            junction_df = pd.concat(
                [
                    junction_df,
                    pd.DataFrame(
                        [{
                            "junction": junction_name,
                            "risk_score": median_risk
                        }]
                    )
                ],
                ignore_index=True
            )

            junction_day_df = pd.concat(
                [
                    junction_day_df,
                    pd.DataFrame(
                        [{
                            "junction": junction_name,
                            "day_type": day_type,
                            "day_multiplier": 1.0
                        }]
                    )
                ],
                ignore_index=True
            )

            junction_hour_df = pd.concat(
                [
                    junction_hour_df,
                    pd.DataFrame(
                        [{
                            "junction": junction_name,
                            "hour": hour,
                            "hour_multiplier": 1.0
                        }]
                    )
                ],
                ignore_index=True
            )

            junction_match = junction_df[
                junction_df["junction"]
                .astype(str)
                .str.lower()
                ==
                junction_name.lower()
            ]

        # =====================================
        # UPDATE RISK SCORE
        # =====================================

        junction_idx = junction_match.index[0]

        old_risk = junction_df.loc[
            junction_idx,
            "risk_score"
        ]

        new_risk = old_risk * correction

        new_risk = max(
            0,
            min(100, new_risk)
        )

        junction_df.loc[
            junction_idx,
            "risk_score"
        ] = round(
            new_risk,
            4
        )

        # =====================================
        # FIND OR CREATE DAY MULTIPLIER
        # =====================================

        day_match = junction_day_df[
            (junction_day_df["junction"]
             .astype(str)
             .str.lower()
             ==
             junction_name.lower())
            &
            (junction_day_df["day_type"]
             ==
             day_type)
        ]

        if day_match.empty:

            junction_day_df = pd.concat(
                [
                    junction_day_df,
                    pd.DataFrame(
                        [{
                            "junction": junction_name,
                            "day_type": day_type,
                            "day_multiplier": 1.0
                        }]
                    )
                ],
                ignore_index=True
            )

            day_match = junction_day_df[
                (junction_day_df["junction"]
                 .astype(str)
                 .str.lower()
                 ==
                 junction_name.lower())
                &
                (junction_day_df["day_type"]
                 ==
                 day_type)
            ]

        day_idx = day_match.index[0]

        old_day = junction_day_df.loc[
            day_idx,
            "day_multiplier"
        ]

        new_day = old_day * correction

        new_day = max(
            0.5,
            min(2.0, new_day)
        )

        junction_day_df.loc[
            day_idx,
            "day_multiplier"
        ] = round(
            new_day,
            4
        )

        # =====================================
        # FIND OR CREATE HOUR MULTIPLIER
        # =====================================

        hour_match = junction_hour_df[
            (junction_hour_df["junction"]
             .astype(str)
             .str.lower()
             ==
             junction_name.lower())
            &
            (junction_hour_df["hour"]
             ==
             hour)
        ]

        if hour_match.empty:

            junction_hour_df = pd.concat(
                [
                    junction_hour_df,
                    pd.DataFrame(
                        [{
                            "junction": junction_name,
                            "hour": hour,
                            "hour_multiplier": 1.0
                        }]
                    )
                ],
                ignore_index=True
            )

            hour_match = junction_hour_df[
                (junction_hour_df["junction"]
                 .astype(str)
                 .str.lower()
                 ==
                 junction_name.lower())
                &
                (junction_hour_df["hour"]
                 ==
                 hour)
            ]

        hour_idx = hour_match.index[0]

        old_hour = junction_hour_df.loc[
            hour_idx,
            "hour_multiplier"
        ]

        new_hour = old_hour * correction

        new_hour = max(
            0.5,
            min(2.0, new_hour)
        )

        junction_hour_df.loc[
            hour_idx,
            "hour_multiplier"
        ] = round(
            new_hour,
            4
        )

    # =====================================
    # UPDATE EVENT SCORE
    # =====================================

    event_match = event_df[
        event_df["event_cause"]
        .astype(str)
        .str.lower()
        ==
        event_type.lower()
    ]

    if not event_match.empty:

        event_idx = event_match.index[0]

        old_event_score = event_df.loc[
            event_idx,
            "event_congestion_score"
        ]

        event_ratio = total_actual / max(
            total_predicted,
            1
        )

        event_error = event_ratio - 1

        # Event block contributes 50%
        event_correction = (
            1 + lr * event_error * 0.5
        )

        new_event_score = (
            old_event_score *
            event_correction
        )

        new_event_score = max(
            0,
            min(100, new_event_score)
        )

        event_df.loc[
            event_idx,
            "event_congestion_score"
        ] = round(
            new_event_score,
            2
        )

    return (
        junction_df,
        junction_day_df,
        junction_hour_df,
        event_df,
    )
    
    
'''
feedback_data = [
    {
        "junction": "MekhriCircle",
        "predicted_officers": 16,
        "actual_officers": 8
    }
]
'''
