import json
import traceback
from datetime import datetime
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import pydeck as pdk
import streamlit as st

import inputs
import text
from helpers import build_results, retrieve_stops_and_lines


def _set_default(key: str, value: Any):
    if key not in st.session_state:
        setattr(st.session_state, key, value)


def main():
    stops, line_ids = retrieve_stops_and_lines()

    defaults = {
        "periods_count": 1,
        "excluded_periods_count": 0,
        "periods_results": [],
        "periods_results_light": [],
    }

    for k, v in defaults.items():
        _set_default(k, v)

    st.markdown(text.HEADER)

    direction_id, filtered_stops, line_name = inputs.line_and_direction_inputs(
        line_ids, stops
    )

    # Filter stops dataframe based on direction selection
    end_segment_index, start_segment_index = inputs.segment_inputs(
        direction_id, filtered_stops
    )

    end_hour, start_hour = inputs.hour_inputs()

    selected_days_human_index = inputs.day_inputs()

    periods = inputs.period_inputs()

    excluded_periods = inputs.excluded_period_inputs()

    selected_compute = inputs.speed_input()

    st.markdown("---")

    # Submit button
    if st.button("Submit analysis", key="submit_analysis"):
        fetch_and_compute(
            direction_id,
            end_hour,
            end_segment_index,
            excluded_periods,
            line_name,
            periods,
            selected_compute,
            selected_days_human_index,
            start_hour,
            start_segment_index,
            stops,
        )

    if st.session_state.periods_results:
        display_results(end_segment_index, start_segment_index)


def display_results(end_segment_index, start_segment_index):
    # Add a divider and information about the analysis time.
    st.divider()
    st.markdown(
        "The analysis is running. Depending on the selected periods, it may take from a few seconds to several minutes."
    )
    # Prepare a list of available periods.
    available_periods = [
        f"Period #{i + 1} ({st.session_state[f'start_date_{i}']} --> {st.session_state[f'end_date_{i}']})"
        for i in range(st.session_state.periods_count)
    ]
    # Add comparison option if more than one period.
    if len(available_periods) > 1:
        available_periods.append("Comparison between all")
    # Select the period to display.
    selected_period = st.selectbox(
        "The period to display",
        options=available_periods,
        index=len(available_periods) - 1,
    )
    # Display results for each selected period.
    for i, (results, results_light) in enumerate(
        zip(st.session_state.periods_results, st.session_state.periods_results_light)
    ):
        if available_periods.index(selected_period) != i:
            continue

        # Extract the selected period's start and end dates.
        start_date = st.session_state[f"start_date_{i}"]
        end_date = st.session_state[f"end_date_{i}"]

        # Process results for better visualization.
        aggregated_results = (
            results.groupby(["stop_sequence", "segment"])
            .agg(avg_speed=("speed", "median"), total_time=("time", "median"))
            .reset_index()
        )

        # Display results for the selected period.
        st.subheader(f"Results for Period {i + 1} ({start_date} - {end_date})")
        st.markdown(
            "Time is computed using speed and the length of the interstop. The speed is based on the distance evolution from the last stop and time between two consecutive points."
        )

        # Create tabs for the chart and data.
        tab_chart, tab_data = st.tabs(["📈 Chart", "🗃 Data"])

        with tab_chart:
            # Average speed per hour.
            tab_chart.markdown("Average speed/hour for the selected segment.")
            hourly_results = results[["date", "speed"]].copy()
            hourly_results["hour"] = pd.to_datetime(hourly_results["date"]).dt.hour
            avg_speed_per_hour = (
                hourly_results.groupby("hour")
                .agg(avg_speed=("speed", "mean"))
                .reset_index()
            )
            tab_chart.bar_chart(avg_speed_per_hour.set_index("hour"))

            # Average speed per interstop.
            tab_chart.markdown("Average speed per interstop for the selected period.")
            fig, ax = plt.subplots()
            aggregated_results.plot(x="segment", y="avg_speed", kind="bar", ax=ax)
            tab_chart.pyplot(fig)

            # Map of average speed per interstop.
            tab_chart.markdown("Average speed per interstop (Map).")
            speed_map = (
                results.groupby(["stop_name", "geometry_y"])
                .agg(avg_speed=("speed", "mean"))
                .reset_index()
                .rename(columns={"geometry_y": "geometry"})
            )

            plot_map(speed_map)

            # Average time per interstop.
            tab_chart.markdown("Average time per interstop for the selected period.")
            aggregated_results = aggregated_results.replace(
                [float("inf"), -float("inf")], float("nan")
            ).dropna()
            fig, ax = plt.subplots()
            aggregated_results.plot(x="segment", y="total_time", kind="bar", ax=ax)
            tab_chart.pyplot(fig)
            tab_chart.divider()

        with tab_data:
            tab_data.markdown(text.RAW_DATA)
            tab_data.dataframe(
                results_light[["segment", "date", "count", "time", "speed"]],
                width=1000,
                column_config={
                    "speed": "Speed (km/h)",
                    "time": "Time (s)",
                    "date": "Date",
                    "count": "Count",
                    "segment": "Segment",
                },
            )
            tab_data.subheader("Results per stop_name:")
            tab_data.write(aggregated_results)

    # Display comparison results across all periods if selected.
    if st.session_state.periods_results and selected_period == "Comparison between all":
        st.header("Results for All Periods")

        # Concatenate results and assign period numbers.
        concatenated_results = pd.concat(
            [
                result.assign(period=str(i + 1))
                for i, result in enumerate(st.session_state.periods_results)
            ]
        )

        # Average speed per hour across periods.
        st.subheader("Average speed/hour for the selected segment across all periods.")
        hourly_results = concatenated_results[["date", "speed", "period"]].copy()
        hourly_results["hour"] = pd.to_datetime(hourly_results["date"]).dt.hour
        avg_speed_per_hour = (
            hourly_results.groupby(["hour", "period"])
            .agg(avg_speed=("speed", "mean"))
            .reset_index()
        )

        # Plot the average speed using matplotlib.
        fig, ax = plt.subplots()
        avg_speed_per_hour.pivot(
            index="hour", columns="period", values="avg_speed"
        ).plot(kind="bar", ax=ax)
        st.pyplot(fig)

        # Line chart of average speed per hour.
        st.line_chart(avg_speed_per_hour, x="hour", y="avg_speed", color="period")

        # Average speed per interstop across periods.
        aggregated_results = (
            concatenated_results.groupby(["stop_name", "period"])
            .agg(avg_speed=("speed", "mean"), total_time=("time", "mean"))
            .reset_index()
        )

        st.subheader(
            "Average speed/interstop for the selected period across all periods."
        )

        # Plot results based on segment selection.
        if start_segment_index == end_segment_index:
            st.scatter_chart(
                aggregated_results, x="stop_name", y="avg_speed", color="period"
            )
        else:
            st.line_chart(
                aggregated_results, x="stop_name", y="avg_speed", color="period"
            )


def plot_map(speed_map):
    gdf = gpd.GeoDataFrame(speed_map, geometry="geometry")
    data = json.loads(gdf.to_json())
    geojson = pdk.Layer(
        "GeoJsonLayer",
        data,
        stroked=False,
        filled=True,
        extruded=True,
        wireframe=True,
        auto_highlight=True,
        get_line_width=15,
        get_line_color="""properties.avg_speed < 6 ? [255, 0, 0] : properties.avg_speed < 9 ? [139, 69, 0] : properties.avg_speed < 12 ? [255, 165, 0] : properties.avg_speed < 18 ? [144, 238, 144] : [0, 100, 0]
                    """,
    )

    deck = pdk.Deck(
        layers=[geojson],
        initial_view_state=pdk.ViewState(
            latitude=50.8,
            longitude=4.35,
            zoom=11,
            max_zoom=16,
            pitch=45,
            bearing=0,
        ),
        tooltip={"text": "{properties.avg_speed}"},
    )
    deck.to_html("out.html")
    st.pydeck_chart(deck)
    st.markdown(
        text.COLOR_BAR,
        unsafe_allow_html=True,
    )


def fetch_and_compute(
    direction_id,
    end_hour,
    end_segment_index,
    excluded_periods,
    line_name,
    periods,
    selected_compute,
    selected_days_human_index,
    start_hour,
    start_segment_index,
    stops,
):
    st.session_state.periods_results = []
    st.session_state.periods_results_light = []
    for period_start, period_end in periods:

        try:
            with st.spinner("Wait for it..."):
                fetch_start = datetime.now()
                results = build_results(
                    stops,
                    line_name,
                    direction_id,
                    selected_days_human_index,
                    start_hour,
                    end_hour,
                    period_start,
                    period_end,
                    start_segment_index,
                    end_segment_index,
                    excluded_periods,
                    selected_compute,
                )
                time_elapsed = datetime.now() - fetch_start
                st.success(
                    f"Analysis completed in {int(time_elapsed.total_seconds())} seconds, Period ({period_start} - {period_end})"
                )
            results = results.sort_values(by="stop_sequence")
            results["segment"] = (
                results["prev_stop_name"] + " -> " + results["stop_name"]
            )

            st.session_state.periods_results.append(results)
            st.session_state.periods_results_light.append(
                results[
                    [
                        "count",
                        "stop_name",
                        "segment",
                        "prev_stop_name",
                        "stop_sequence",
                        "date",
                        "time",
                        "speed",
                    ]
                ]
            )
        except Exception as e:
            st.exception(e)


if __name__ == "__main__":
    main()
