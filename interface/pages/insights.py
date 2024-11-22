from typing import Any

import altair as alt
import streamlit as st

from domain.helpers import (
    retrieve_stops_and_lines,
    build_results,
    remove_speed_outliers,
)
from interface import inputs


def _set_default(key: str, value: Any):
    if key not in st.session_state:
        setattr(st.session_state, key, value)


def insights_view():
    st.header("STIB Insights")

    stops, line_ids = retrieve_stops_and_lines()

    defaults = {
        "periods_count": 1,
        "excluded_periods_count": 0,
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

    period_start, period_end = inputs.single_period_input()

    excluded_periods = inputs.excluded_period_inputs(
        periods=[(period_start, period_end)]
    )

    selected_compute = inputs.speed_input()

    if st.button("Compute"):
        with st.spinner("Crunching through millions of data points..."):
            st.session_state["results"] = None
            results = remove_speed_outliers(
                build_results(
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
            )
            st.session_state["results"] = results

    if st.session_state.get("results") is not None:
        results = st.session_state["results"]

        average_speed_overall = results["speed"].mean()

        st.metric(
            "Average speed",
            f"{average_speed_overall:0.2f}",
            help="Expressed in km/h",
        )

        # Plot average speed per month
        st.write("### Average speed per month")
        # set date as index
        results.set_index("date", inplace=True, drop=False)
        st.line_chart(
            results["speed"].resample("ME").mean(),
            x_label="Month",
            y_label="Average speed (km/h)",
        )

        # Average speed per day of the week
        st.write("### Average speed per day of the week")
        results["day_of_week"] = (results.index.day_of_week + 1).astype(str)
        results["day_of_week_name"] = (results.index.day_name()).astype(str)

        df_per_day_of_the_week = (
            results.groupby(["day_of_week", "day_of_week_name"])[["speed"]]
            .mean()
            .reset_index()
        )
        st.altair_chart(
            alt.Chart(df_per_day_of_the_week)
            .mark_bar()
            .encode(
                x=alt.X("day_of_week_name", title="Day of the week", sort=None),
                y=alt.Y("speed", title="Average speed (km/h)", sort=None),
            ),
            use_container_width=True,
        )

        # The same but boxplot with matplotlib
        st.write("### Boxplot of speed per day of the week")

        st.altair_chart(
            alt.Chart(
                results[["day_of_week_name", "day_of_week", "speed"]]
                .copy()
                .sort_values("day_of_week")
            )
            .mark_boxplot()
            .encode(
                x=alt.X("day_of_week_name", title="Day of the week", sort=None),
                y=alt.Y("speed", title="Speed (km/h)", sort=None),
            ),
            use_container_width=True,
        )

        # Boxplot of speed per hour
        st.write("### Boxplot of speed per hour")
        results["hour"] = results.index.hour
        st.bar_chart(
            results.groupby("hour")["speed"].mean(),
            x_label="Hour",
            y_label="Average speed (km/h)",
        )
