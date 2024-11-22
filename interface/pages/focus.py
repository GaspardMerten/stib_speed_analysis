import logging
from datetime import datetime
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from domain.helpers import build_results, retrieve_stops_and_lines
from interface import inputs, text
import geopandas as gpd
import pydeck as pdk
import json

from interface.plot_map import plot_map


def _set_default(key: str, value: Any):
    if key not in st.session_state:
        setattr(st.session_state, key, value)


SPEED_COLOR_DOMAIN = [6, 9, 12, 18, 60]
SPEED_COLOR_RANGE = [
    "rgb(255, 0, 0)",  # Red for 0-6
    "rgb(255, 145, 0)",  # Dark Orange for 6-9
    "rgb(255, 204, 0)",  # Orange for 9-12
    "rgb(144, 238, 144)",  # Light Green for 12-15
    "rgb(50, 128, 50)",  # Light Green for 15-18
    "rgb(0, 100, 0)",  # Dark Green for >18
]

logging.basicConfig(level=logging.INFO)


def focus_view():
    st.header("STIB Focus Analysis")
    st.markdown(
        text.FOCUS,
        unsafe_allow_html=True,
    )

    stops, line_ids = retrieve_stops_and_lines()

    defaults = {
        "periods_count": 1,
        "excluded_periods_count": 0,
        "periods_results": [],
        "periods_results_light": [],
    }

    for k, v in defaults.items():
        _set_default(k, v)

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

    excluded_periods = inputs.excluded_period_inputs(periods)

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


@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode("utf-8")


def display_results(end_segment_index, start_segment_index):
    st.divider()
    st.title("Results")
    st.markdown(
        "Below are the results for the query you submitted. If you selected multiple periods, you can choose to display the results of the comparison, or of each period individually."
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
            "Time is computed using speed and the length of the interstop . The speed is based on the distance evolution from the last stop and time between two consecutive points."
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
            # equivalent with altair
            chart = (
                alt.Chart(avg_speed_per_hour)
                .mark_bar()
                .encode(
                    x=alt.X("hour", title="Hour", type="ordinal"),
                    y=alt.Y(
                        "avg_speed",
                        title="Average speed (km/h)",
                        scale=alt.Scale(domain=[0, 20]),
                    ),
                    tooltip=["hour", "avg_speed"],
                )
            )

            tab_chart.altair_chart(chart, use_container_width=True)

            # Average speed per interstop .
            tab_chart.markdown("Average speed per interstop  for the selected period.")

            chart = (
                alt.Chart(aggregated_results)
                .mark_bar()
                .encode(
                    x=alt.X("segment", title="Segment", sort=None),
                    y=alt.Y(
                        "avg_speed",
                        title="Average speed (km/h)",
                        scale=alt.Scale(domain=[0, 20]),
                    ),
                    tooltip=["segment", "avg_speed"],
                )
                .properties(height=500)
            )

            tab_chart.altair_chart(chart, use_container_width=True)

            # Map of average speed per interstop .
            tab_chart.markdown("Average speed per interstop  (Map).")

            plot_map(results)

            # Average time per interstop .
            tab_chart.markdown("Average time per interstop  for the selected period.")
            aggregated_results = aggregated_results.replace(
                [float("inf"), -float("inf")], float("nan")
            ).dropna()

            # with altair
            chart = (
                alt.Chart(aggregated_results)
                .mark_bar()
                .encode(
                    x=alt.X("segment", title="Segment", sort=None),
                    y=alt.Y(
                        "total_time",
                        title="Average time (s)",
                    ),
                    color=alt.Color(
                        "total_time", legend=None, scale=alt.Scale(scheme="teals")
                    ),
                    tooltip=["segment", "total_time"],
                )
                .properties(height=500)
            )

            tab_chart.altair_chart(chart, use_container_width=True)

            tab_chart.divider()

        with tab_data:
            tab_data.markdown(text.RAW_DATA)
            tab_data.dataframe(
                results_light[
                    [
                        "count",
                        "stop_name",
                        "prev_stop_name",
                        "segment",
                        "stop_sequence",
                        "date",
                        "time",
                        "speed",
                    ]
                ],
                column_config={
                    "speed": "Speed (km/h)",
                    "prev_stop_name": "Previous Stop",
                    "stop_name": "Stop",
                    "time": "Time (s) (interstop  length / speed)",
                    "date": "Date",
                    "stop_sequence": "Stop Sequence",
                    "count": "Count",
                    "segment": "Segment",
                },
            )
            tab_data.download_button(
                "Download data as CSV",
                convert_df(results_light),
                f"results_{start_segment_index}_{end_segment_index}_{start_date}_{end_date}.csv",
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
        st.subheader("Average speed/hour for the complete segment for each period.")
        hourly_results = concatenated_results[["date", "speed", "period"]].copy()
        hourly_results["hour"] = pd.to_datetime(hourly_results["date"]).dt.hour
        avg_speed_per_hour = (
            hourly_results.groupby(["hour", "period"])
            .agg(avg_speed=("speed", "mean"))
            .reset_index()
        )

        # Equivalent with altair
        chart = (
            alt.Chart(avg_speed_per_hour)
            .mark_line()
            .encode(
                x=alt.X("hour", title="Hour", type="ordinal"),
                y=alt.Y(
                    "avg_speed",
                    title="Average speed (km/h)",
                    scale=alt.Scale(domain=[0, 20]),
                ),
                color=alt.Color("period"),
                tooltip=["hour", "avg_speed"],
            )
        )

        st.altair_chart(chart, use_container_width=True)

        # Average speed per interstop  across periods.
        aggregated_results = (
            concatenated_results.groupby(["stop_name", "period", "stop_sequence"])
            .agg(avg_speed=("speed", "mean"), total_time=("time", "mean"))
            .reset_index()
        )

        st.subheader(
            "Average speed/interstop  for the selected period across all periods."
        )

        # Plot results based on interstop selection.
        if start_segment_index == end_segment_index:
            st.scatter_chart(
                aggregated_results, x="stop_name", y="avg_speed", color="period"
            )
        else:
            # with altair
            chart = (
                alt.Chart(aggregated_results.sort_values("stop_sequence"))
                .mark_line()
                .encode(
                    x=alt.X("stop_name", title="Segment", sort=None),
                    y=alt.Y(
                        "avg_speed",
                        title="Average speed (km/h)",
                        sort=None,
                    ),
                    color=alt.Color("period"),
                    tooltip=["stop_name", "avg_speed"],
                )
                .properties(height=500)
            )

            st.altair_chart(chart, use_container_width=True)


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
