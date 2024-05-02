import json
from datetime import timedelta

import geopandas
import pandas as pd
import streamlit as st

from query import get_average_speed_for


@st.cache_data
def get_stops(_client):
    stops = json.loads(_client.get_last_item("stib_stops").data)
    stops_gdf = geopandas.GeoDataFrame.from_features(stops)
    # Sort stops_gdf by route_short_name, direction, stop_sequence
    stops_gdf.sort_values(by=["route_short_name", "direction", "stop_sequence"], inplace=True)

    # rename route_short_name to lineId
    stops_gdf.rename(columns={"route_short_name": "lineId"}, inplace=True)

    # Use lag to get the next stop_id (per lineId, direction)
    stops_gdf["next_stop_id"] = stops_gdf.groupby(["lineId", "direction"])["stop_id"].shift(-1)

    # Remove rows where next_stop_id is next_stop_id
    stops_gdf = stops_gdf.dropna(subset=["next_stop_id"])

    # Convert stop_id and next_stop_id to integers
    stops_gdf["stop_id"] = stops_gdf["stop_id"].astype(int)
    stops_gdf["next_stop_id"] = stops_gdf["next_stop_id"].astype(int)

    return stops_gdf


@st.cache_data
def get_segments(_client, line_id, direction_id: int):
    shapefile = _client.get_last_item("stib_segments")
    sh = json.loads(shapefile.data)
    segments_gdf = geopandas.GeoDataFrame.from_features(sh)
    segments_gdf = segments_gdf[(segments_gdf["line_id"] == line_id) & (segments_gdf["direction"] == direction_id + 1)]
    # change direction column to be the map direction
    segments_gdf["direction"] = direction_id - 1
    segments_gdf["delta_distance"] = segments_gdf["distance"].diff()

    return segments_gdf


def build_results(client, stops, line_name, direction_id, selected_days_human_index, start_hour, end_hour, start_date,
                  end_date, start_stop_index, end_stop_index, excluded_periods, speed_type):
    all_stops = get_stops(client)

    segments = get_segments(client, line_name, direction_id)
    # drop direction column
    segments = segments.drop(columns=["direction"])
    # Merge stops with segments
    stops = stops.merge(segments, left_on=["next_stop_id", "lineId"], right_on=["start", "line_id"])
    print(start_stop_index, start_stop_index)
    print(stops)
    # Print all stops for the selected line and direction, ask user to select index range
    stops = stops[stops["direction"] == direction_id].sort_values(by="stop_sequence").reset_index(drop=True)
    selected_stops = stops.loc[start_stop_index:end_stop_index]

    stop_ids = [str(row["stop_id"]) for index, row in selected_stops.iterrows()]

    selected_period = [start_date, end_date]

    results = None

    # iterate over each day of the selected period
    for day in range((selected_period[1] - selected_period[0]).days + 1):
        if any([selected_period[0] <= excluded_period[0] <= selected_period[1] for excluded_period in excluded_periods]):
            continue

        if (selected_period[0] + timedelta(day)).weekday() - 1 not in selected_days_human_index:
            continue

        day_results = get_average_speed_for(
            client, line_name, stop_ids,
            selected_period[0] + timedelta(days=day),
            selected_period[0] + timedelta(day + 1),
            selected_days_human_index, start_hour, end_hour,
            aggregation="date_trunc('hour', {date})",
            speed_type=speed_type
        )
        if results is not None:
            results = pd.concat([results, day_results])
        else:
            results = day_results

    # Convert pointId to integer
    results["pointId"] = results["pointId"].astype(int)
    # Merge the results with the selected_stops
    results = selected_stops.merge(results, left_on="stop_id", right_on="pointId")

    def get_stop_name(stop_id):
        if isinstance(stop_id, str):
            stop_id = int(stop_id)
        try:
            return all_stops[all_stops["stop_id"] == stop_id]["stop_name"].values[0]
        except IndexError:
            return f"Stop ID {stop_id}"

    results["direction_stop_name"] = results["directionId"].apply(get_stop_name)
    results["next_stop_name"] = results["next_stop_id"].apply(get_stop_name)
    results["time"] = results["delta_distance"] / (results["speed"] / 3.6)

    return results
