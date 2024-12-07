import os
import time

import streamlit as st

from interface.pages.focus import focus_view
from interface.pages.home import home_view
from interface.pages.insights import insights_view
from interface.pages.trips import trips_view

# SET TIMEZONE AS Europe/Brussels
os.environ["TZ"] = "Europe/Brussels"
time.tzset()


def main():
    st.set_page_config(page_title="STIB Speed Analysis")

    st.logo("https://mobilitytwin.brussels/static/logo.png", size="large")

    home = st.Page(
        home_view,
        title="Home",
        icon=":material/home:",
    )

    focus = st.Page(
        focus_view,
        title="Focus",
        url_path="/focus",
        icon=":material/zoom_in:",
    )

    insights = st.Page(
        insights_view,
        title="Insights",
        url_path="/insights",
        icon=":material/star:",
    )
    trips = st.Page(
        trips_view,
        title="Trips (experimental)",
        url_path="/trips",
        icon=":material/map:",
    )

    pg = st.navigation(
        [home, focus, insights, trips],
    )

    pg.run()


if __name__ == "__main__":
    main()
