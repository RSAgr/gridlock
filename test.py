import pandas as pd
from modules.calculate_officers import calculate_officers

junction_scores_df = pd.read_csv("datasets/junction_scores.csv")
junction_day_df = pd.read_csv("datasets/junction_daytype_multipliers.csv")
junction_hour_df = pd.read_csv("datasets/junction_hour_multipliers.csv")
event_df = pd.read_csv("datasets/event_congestion_scores.csv")

result = calculate_officers(
    junction_name="AnepalyaJunc",
    event_type="tree_fall",
    day_type="Weekday",
    hour=17,
    start_time="2026-06-21 17:00:00",
    junction_scores_df=junction_scores_df,
    junction_day_df=junction_day_df,
    junction_hour_df=junction_hour_df,
    event_df=event_df
)

print(result)