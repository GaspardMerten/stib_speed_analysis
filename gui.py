import motion_lake_client
import pandas as pd
import streamlit as st

from helpers import get_stops, build_results

client = motion_lake_client.BaseClient("http://52.146.145.19:8000")

stops = get_stops(client)

# Metro lines 1, 2, 3, 5 are not used in the analysis
line_ids_to_drop = ["1", "2", "3", "5"]
stops = stops[~stops["lineId"].isin(line_ids_to_drop)]


# Streamlit form for user inputs
def main():
    if 'excluded_periods_count' not in st.session_state:
        st.session_state.excluded_periods_count = 0

    if 'periods_count' not in st.session_state:
        st.session_state.periods_count = 1

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
    filtered_stops = filtered_stops[
        filtered_stops["direction"] == direction_name
        ].copy().reset_index(drop=True)

    start_stop_name = st.selectbox("Select the index of the start stop:", filtered_stops["stop_name"].values, index=0)
    end_stop_name = st.selectbox("Select the index of the end stop:", filtered_stops["stop_name"].values,
                                 index=len(filtered_stops["stop_name"].values) - 1)

    start_stop_index = filtered_stops[filtered_stops["stop_name"] == start_stop_name].index[0]
    end_stop_index = filtered_stops[filtered_stops["stop_name"] == end_stop_name].index[0]

    start_hour = st.number_input("Enter the start hour (0-23):", min_value=0, max_value=23)
    end_hour = st.number_input("Enter the end hour (0-23):", min_value=0, max_value=23, value=23)
    selected_days_human_index = st.multiselect("Enter days of the week selected days (1=Monday, ...): e.g 357",
                                               [1, 2, 3, 4, 5, 6, 7], [1, 2, 3, 4, 5, 6, 7])

    # the same but allow to add multiple periods
    periods = []

    for i in range(st.session_state.periods_count):
        feature = (
            st.date_input(f"Period {i + 1} - Start date", key=f"start_date_{i}"),
            st.date_input(f"Period {i + 1} - End date", key=f"end_date_{i}")
        )
        periods.append(feature)

    if st.button("Add new period"):
        print("Adding new period", st.session_state.periods_count)
        st.session_state.periods_count += 1
        # refresh the page
        st.rerun()

    # Add text to explain how the speed computation mode works (the text is hidden by default ,there is a button to show it), now put it in a container
    # Define a CSS style to create a lighted background
    st.markdown(
        """
        <style>
        .container {
            background-color: #f0f0f5;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.1);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Wrap the text inside a container
    st.markdown("""
    <div class='st-bb' style='padding: 16px; border-radius: 8px; margin-bottom: 8px;' >
     <h3>Speed computation mode</h3>
     <p>The speed computation mode is used to filter the results based on the speed computed. The speed is computed
     using the evolution of the distance from the last stop and the time between two consecutive points. This data is
     refreshed every 20 seconds, meaning some uncertainties can be present in the results, particularly when the
        vehicle is stopped. The following modes are available: </p>
        <ul>
            <li><strong>Speed >= 0</strong>: This mode will include all the results where the speed is greater or equal to 0.</li>
            <li><strong>Speed >= 0 but not 0 if close to stop</strong>: This mode will include all the results where the speed is greater or equal to 0, but not 0 if the stop is close to the stop.</li>
            <li><strong>Speed > 0</strong>: This mode will include all the results where the speed is greater than 0.</li>
        </ul>
        The first one is the most pessimistic, the last one is the most optimistic.
    </div>
    """, unsafe_allow_html=True)

    # A switch to select the speed computation mode, for each mode, explain what it does
    switch = st.selectbox(
        "Select speed computation mode",
        [
            "Speed >= 0",
            "Speed >= 0 but not 0 if close to stop",
            "Speed > 0"
        ]
    )

    # Allow to specify excluded periods (e.g. holidays (so as many start, end dates as needed))
    st.write("Excluded periods")

    excluded_periods = []

    for i in range(st.session_state.excluded_periods_count):
        feature = (st.date_input("Start date", key=f"excluded_start_date_{i}" + '_1'),
                   st.date_input("End date", key=f"excluded_end_date_{i}" + '_1'))
        excluded_periods.append(feature)

    if st.button("Add new excluded period"):
        st.session_state.excluded_periods_count += 1
        # refresh the page
        st.rerun()

    # Submit button
    if st.button("Submit"):
        concatenated_results = []

        for i in range(st.session_state.periods_count):
            selected_period_start = st.session_state[f"start_date_{i}"]
            selected_period_end = st.session_state[f"end_date_{i}"]

            # Call your existing code with the provided inputs
            results = build_results(
                client, stops, line_name, direction_name, selected_days_human_index, start_hour,
                end_hour,
                selected_period_start, selected_period_end, start_stop_index, end_stop_index,
                excluded_periods,
                switch
            )

            results = results.sort_values(by="stop_sequence")

            concatenated_results.append(results)

            results_light = results[
                ["count", "stop_name", "direction_stop_name", "next_stop_name", "date", "time", "speed"]]

            # Add a title
            st.subheader(f"Results for period {i + 1} ({selected_period_start} - {selected_period_end})")

            # Display the results
            st.write(results_light)

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

            # drop na/inf
            # Plot
            st.line_chart(new_results.set_index("date"))

            # Now do the same but per stop_name (so avg speed per stop_name)
            new_results = results.groupby("stop_name").agg(
                avg_speed=("speed", "mean"),
                total_time=("time", "mean")
            ).reset_index()

            st.write("Results per stop_name:")
            st.write(new_results)
            st.write("Results per stop_name, avg speed")
            st.line_chart(new_results.set_index("stop_name")[["avg_speed"]])
            st.write("Results per stop_name, total time")
            new_results = new_results.replace([float('inf'), -float('inf')], float('nan'))
            # drop na
            new_results = new_results.dropna()
            st.line_chart(new_results.set_index("stop_name")[["total_time"]])

            avg_speed_per_line = results.groupby(["stop_name", "geometry_y"]).agg(
                avg_speed=("speed", "mean"),
            ).reset_index().rename(columns={"geometry_y": "geometry"})
            import geopandas as gpd
            import matplotlib.pyplot as plt

            figure, ax = plt.subplots()
            gdf = gpd.GeoDataFrame(avg_speed_per_line, geometry="geometry")
            gdf.plot(column="avg_speed", legend=True, ax=ax)

            st.pyplot(figure)

        # Plot the evolution of the speed per stop_name for all the periods (so one line per period)
        if concatenated_results:
            # assign a period number to each result
            for i, result in enumerate(concatenated_results):
                result["period"] = i + 1

            concatenated_results = pd.concat(concatenated_results)
            new_results = concatenated_results.groupby(["stop_name", "period"]).agg(
                avg_speed=("speed", "mean"),
                total_time=("time", "mean")
            ).reset_index()

            st.header("Results for all periods")
            st.write("Results per stop_name, one line per period")

            st.line_chart(new_results, x="stop_name", y="avg_speed", color="period")


if __name__ == "__main__":
    main()
