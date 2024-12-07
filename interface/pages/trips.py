import time
from collections import defaultdict
from datetime import timedelta, datetime

import pydeck
import requests
import streamlit as st


def hex_to_rgb(
    hex,
):
    r = int(hex[1:3], 16)
    g = int(hex[3:5], 16)
    b = int(hex[5:7], 16)
    return [r, g, b]


def get_trips(start, end):
    url = "https://api.mobilitytwin.brussels/stib/vehicle-position"

    delta = timedelta(seconds=20)

    trips = defaultdict(lambda: {"timestamps": [], "path": [], "color": ""})
    current_time = start
    while current_time < end:
        timestamp = int(current_time.timestamp())
        current_time += delta
        response = requests.get(
            url + f"?timestamp={timestamp}",
            headers={
                "Authorization": "Bearer 42227799ae2e74ebc42ca66dee38f4352456c2e93a21962133e0056fd228392eecd70222df0a0c3882438acdfb59de933c50ef368cebb8f5ab8b19d3bd8d2134"
            },
        )

        current = response.json()

        for feature in current["features"]:
            vehicle_id = feature["id"]
            trips[vehicle_id]["timestamps"].append(int(timestamp - start.timestamp()))
            trips[vehicle_id]["path"].append(feature["geometry"]["coordinates"])
            trips[vehicle_id]["color"] = hex_to_rgb(feature["properties"]["color"])

    return trips


def trips_view():
    st.header("STIB Trips")
    st.text("A simple visualization of STIB trips. Allows to see reconstructed trips.")
    st.text("Limitation: cannot display data for more than 15 minuts.")
    day = st.date_input("Select the day", value=datetime.now(), key="day")
    col1, col2 = st.columns([1, 1])
    with col1:
        start_time = st.time_input("Start time", key="start_time")
    with col2:
        end_time = st.time_input("End time", key="end_time")

    replay_speed = st.slider(
        "Replay speed (how many seconds to show per 1 second), 1 means same speed",
        min_value=1,
        max_value=20,
        value=1,
        step=1,
    )

    if not st.button("Load and display trips"):
        return

    start = datetime.combine(day, start_time)
    end = datetime.combine(day, end_time)
    print(start, end)
    if (end - start).seconds > 900:
        st.error("The maximum duration is 15 minutes.")
        return

    with st.spinner("Loading trips..."):
        trips = get_trips(
            start,
            end,
        )

    print(trips)
    latest_timestamp = max(max(trip["timestamps"]) for trip in trips.values())

    trip_layer = pydeck.Layer(
        "TripsLayer",
        id="trips-layer",
        data=list(trips.values()),
        get_timestamps="timestamps",
        get_path="path",
        current_time=0,
        trail_length=500,
        width_min_pixels=4,
        rounded=True,
        get_color="color",
    )

    deck = pydeck.Deck(
        initial_view_state=pydeck.ViewState(
            latitude=50.85045,
            longitude=4.34878,
            zoom=12,
            pitch=50,
        ),
        layers=[trip_layer],
    )

    placeholder = st.empty()

    for i in range(latest_timestamp // replay_speed):
        with placeholder.container():
            st.progress(round(i / (latest_timestamp // replay_speed) * 100))
            st.pydeck_chart(deck)
            trip_layer.current_time += replay_speed
            time.sleep(1)
