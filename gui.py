import random
import string

import motion_lake_client
import streamlit as st

from helpers import get_stops, build_results

client = motion_lake_client.BaseClient("http://52.146.145.19:8000")

stops = get_stops(client)


# Streamlit form for user inputs
def main():
    st.title("Live STIB data analysis")

    # Input fields
    line_name = st.selectbox("Select a line from the following list:", stops["lineId"].unique())

    # Filter stops dataframe based on line selection
    filtered_stops = stops[stops["lineId"] == line_name]

    # Get unique directions for the selected line
    unique_directions = filtered_stops["direction"].unique()

    # Input field for direction
    direction_name = st.selectbox("Select a direction:", unique_directions)

    # Filter stops dataframe based on direction selection
    filtered_stops = filtered_stops[filtered_stops["direction"] == direction_name].copy().reset_index(drop=True)

    start_stop_name = st.selectbox("Select the index of the start stop:", filtered_stops["stop_name"].values, index=0)
    end_stop_name = st.selectbox("Select the index of the end stop:", filtered_stops["stop_name"].values,
                                 index=len(filtered_stops["stop_name"].values) - 1)

    start_stop_index = filtered_stops[filtered_stops["stop_name"] == start_stop_name].index[0]
    end_stop_index = filtered_stops[filtered_stops["stop_name"] == end_stop_name].index[0]

    start_hour = st.number_input("Enter the start hour (0-23):", min_value=0, max_value=23)
    end_hour = st.number_input("Enter the end hour (0-23):", min_value=0, max_value=23, value=23)
    selected_days_human_index = st.multiselect("Enter days of the week selected days (1=Monday, ...): e.g 357",
                                               [1, 2, 3, 4, 5, 6, 7], [1, 2, 3, 4, 5, 6, 7])
    selected_period_start = st.date_input("Enter start date for the selected period:")
    selected_period_end = st.date_input("Enter end date for the selected period:")

    # Allow to specify excluded periods (e.g. holidays (so as many start, end dates as needed))
    st.write("Excluded periods")

    if 'excluded_periods_count' not in st.session_state:
        st.session_state.excluded_periods_count = 0

    excluded_periods = []

    for i in range(st.session_state.excluded_periods_count):
        feature = (st.date_input("Start date", key=f"start_date_{i}" + '_1'),
                   st.date_input("End date", key=f"end_date_{i}" + '_1'))
        excluded_periods.append(feature)

    if st.button("Add new excluded period"):
        st.session_state.excluded_periods_count += 1
        # refresh the page
        st.rerun()

    # Submit button
    if st.button("Submit"):
        # Call your existing code with the provided inputs
        results = build_results(
            client, stops, line_name, direction_name, selected_days_human_index, start_hour,
            end_hour,
            selected_period_start, selected_period_end, start_stop_index, end_stop_index,
            excluded_periods
        )

        # Display the results
        st.write(results)

        # Compute abg speed and distance per stop_name and date
        new_results = results.groupby(["stop_name", "date"]).agg(
            avg_speed=("speed", "mean"),
            total_time=("time", "mean")
        ).reset_index()

        # Now compute the avg speed and cumulative time per date
        new_results = new_results.groupby("date").agg(
            avg_speed=("avg_speed", "mean"),
        ).reset_index()

        st.write("Results per date:")
        st.write(new_results)

        # Plot
        st.line_chart(new_results.set_index("date"))


if __name__ == "__main__":
    main()
