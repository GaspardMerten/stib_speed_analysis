from typing import Any

import streamlit as st
import altair as alt
from domain.helpers import (
    retrieve_stops_and_lines,
    build_results,
    remove_speed_outliers,
)
from interface import inputs
from interface.elements import card_number


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

    end_hour, start_hour = inputs.hour_inputs()

    selected_days_human_index = inputs.day_inputs()

    period_start, period_end = inputs.single_period_input()

    excluded_periods = inputs.excluded_period_inputs()

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
                    0,
                    len(filtered_stops) - 1,
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
            results["speed"].resample("M").mean(),
            x_label="Month",
            y_label="Average speed (km/h)",
        )

        # Average speed per day of the week
        st.write("### Average speed per day of the week")
        results["day_of_week"] = results.index.day_name()
        st.bar_chart(results.groupby("day_of_week")["speed"].mean())

        # The same but boxplot with matplotlib
        st.write("### Boxplot of speed per day of the week")

        import matplotlib.pyplot as plt
        import seaborn as sns

        fig, ax = plt.subplots()
        sns.boxplot(x="day_of_week", y="speed", data=results, ax=ax)
        st.pyplot(fig)

        # Boxplot of speed per hour
        st.write("### Boxplot of speed per hour")
        results["hour"] = results.index.hour
        st.bar_chart(
            results.groupby("hour")["speed"].mean(),
            x_label="Hour",
            y_label="Average speed (km/h)",
        )
