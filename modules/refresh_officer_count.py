import pandas as pd


def refresh_officer_availability(
    resources_file="datasets/police_station_resources.csv",
    deployments_file="datasets/police_deployments.csv",
    current_time=None
):
    """
    Returns officers from expired deployments.

    Parameters
    ----------
    current_time : str
        Example:
        "2026-06-21 19:00:00"
    """

    if current_time is None:
        current_time = pd.Timestamp.now()

    current_time = pd.to_datetime(current_time)

    # Load files
    resources_df = pd.read_csv(resources_file)

    deployments_df = pd.read_csv(deployments_file)

    # Empty deployment file
    if deployments_df.empty:
        print("No active deployments found.")
        return resources_df

    # Convert times
    deployments_df["end_time"] = pd.to_datetime(
        deployments_df["end_time"]
    )

    # Find expired deployments
    expired = deployments_df[
        deployments_df["end_time"] <= current_time
    ]

    if expired.empty:
        print("No deployments expired.")
        return resources_df

    print("\nReturned Officers")

    # Return officers
    for _, row in expired.iterrows():

        station = row["station_name"]

        officers = row["officers"]

        resources_df.loc[
            resources_df["station_name"] == station,
            "available_officers"
        ] += officers

        print(
            f"{station} -> +{officers} officers"
        )

    # Keep only active deployments
    deployments_df = deployments_df[
        deployments_df["end_time"] > current_time
    ]

    # Save updated files
    resources_df.to_csv(
        resources_file,
        index=False
    )

    deployments_df.to_csv(
        deployments_file,
        index=False
    )

    print(
        f"\nRemaining Active Deployments: {len(deployments_df)}"
    )

    return resources_df