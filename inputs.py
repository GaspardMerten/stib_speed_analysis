from datetime import timedelta, datetime

import streamlit as st

import text
from query import SpeedComputationMode


def speed_input():
    st.markdown(text.SPEED, unsafe_allow_html=True)
    # A switch to select the speed computation mode, for each mode, explain what it does
    switch = st.selectbox(
        "Select speed computation mode",
        ["Speed >= 0", "Speed >= 0 but not 0 if close to stop", "Speed > 0"],
    )
    compute_map = {
        "Speed >= 0": SpeedComputationMode.ALL,
        "Speed >= 0 but not 0 if close to stop": SpeedComputationMode.GREATER_THAN_ZERO_IF_CLOSE_TO_STOP,
        "Speed > 0": SpeedComputationMode.GREATER_THAN_ZERO,
    }
    selected_compute = compute_map[switch]
    return selected_compute


def excluded_period_inputs():
    st.markdown(
        "---\n*Please select the different periods you want to exclude from the analysis, for instance holidays. This is **not mandatory**.*\n"
    )
    excluded_periods = []
    for i in range(st.session_state.excluded_periods_count):
        feature = (
            st.date_input("Start date", key=f"excluded_start_date_{i}"),
            st.date_input("End date", key=f"excluded_end_date_{i}"),
        )
        excluded_periods.append(feature)
    if st.button("Add excluded period"):
        st.session_state.excluded_periods_count += 1
        # refresh the page
        st.rerun()
    if st.session_state.excluded_periods_count > 1 and st.button(
        "Remove last excluded period"
    ):
        st.session_state.excluded_periods_count -= 1
        # refresh the page
        st.rerun()
    return excluded_periods


def period_inputs():
    st.markdown(
        "---\n*Please select the different periods you want to analyze, the average speed will be computed for each "
        "period, then the results will be displayed together for quick comparison.*\n"
    )
    st.info(
        "Data is available from 2023-02-25 to today, to the exception of the 2024-07-11 to 2024-08-11 period which is "
        "not available.",
    )
    # the same but allow to add multiple periods
    periods = []
    for i in range(st.session_state.periods_count):
        col1, col2 = st.columns([1, 1])
        with col1:
            start_input = col1.date_input(
                f"Period {i + 1} - Start date",
                key=f"start_date_{i}",
                value=datetime.now() - timedelta(days=8),
                min_value=datetime(2023, 3, 1),
                max_value=datetime.now() - timedelta(days=1),
            )
        with col2:
            end_input = col2.date_input(
                f"Period {i + 1} - End date",
                key=f"end_date_{i}",
                value=datetime.now() - timedelta(days=1),
                min_value=datetime(2023, 3, 1),
                max_value=datetime.now() - timedelta(days=1),
            )
        feature = (
            start_input,
            end_input,
        )
        periods.append(feature)
    if st.session_state.periods_count > 1 and st.button("Remove last period"):
        st.session_state.periods_count -= 1
        # refresh the page
        st.rerun()
    if st.button("Add new period"):
        st.session_state.periods_count += 1
        # refresh the page
        st.rerun()

    return periods


def day_inputs():
    selected_days_human_index = st.multiselect(
        "Enter days of the week selected days (1=Monday, ...): e.g 357",
        [1, 2, 3, 4, 5, 6, 7],
        [1, 2, 3, 4, 5, 6, 7],
    )
    return selected_days_human_index


def hour_inputs():
    st.markdown(
        "---\n*The start and end hours are inclusive, meaning that if 7 is selected, it contains 7h00 to 7h59*"
    )
    col1, col2 = st.columns([1, 1])
    with col1:
        start_hour = col1.number_input(
            "Enter the start hour (0-23):", min_value=0, max_value=23, value=6
        )
    with col2:
        end_hour = col2.number_input(
            "Enter the end hour (0-23):", min_value=0, max_value=23, value=23
        )
    return end_hour, start_hour


def segment_inputs(direction_id, filtered_stops):
    filtered_stops = (
        filtered_stops[filtered_stops["direction"] == direction_id]
        .copy()
        .reset_index(drop=True)
    )
    st.markdown(
        "---\n*Please select the start and end segment. Note that segments between start and end are included, "
        "for one single segment, select the same start and end.*\n"
    )
    start_segment_name = st.selectbox(
        "Select the index of the start segment:",
        filtered_stops["segment_name"].values,
        index=0,
    )
    stop_segment_name = st.selectbox(
        "Select the index of the end segment:",
        filtered_stops["segment_name"].values,
        index=len(filtered_stops["stop_name"].values) - 1,
    )
    start_segment_index = filtered_stops[
        filtered_stops["segment_name"] == start_segment_name
    ].index[0]
    end_segment_index = (
        filtered_stops[filtered_stops["segment_name"] == stop_segment_name].index[0] - 1
    )
    return end_segment_index, start_segment_index


def line_and_direction_inputs(line_ids, stops):
    col1, col2 = st.columns([1, 2])
    # Input fields
    with col1:
        line_name = col1.selectbox("Line", line_ids, index=list(line_ids).index("60"))
    # Filter stops dataframe based on line selection
    filtered_stops = stops[stops["lineId"] == line_name]
    # Get unique directions for the selected line
    unique_directions = filtered_stops["direction"].unique()
    unique_directions_names = {}
    for direction in unique_directions:
        last_stop_name = (
            filtered_stops[filtered_stops["direction"] == direction]
            .sort_values(by="stop_sequence")["stop_name"]
            .values[-1]
        )

        unique_directions_names[last_stop_name] = direction
    with col2:
        direction_name = st.selectbox(f"Direction", unique_directions_names.keys())
    direction_id = unique_directions_names[direction_name]
    return direction_id, filtered_stops, line_name
