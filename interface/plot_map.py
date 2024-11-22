import json

import geopandas as gpd
import pydeck as pdk
import streamlit as st

from interface import text


def plot_map(results):
    speed_map = (
        results.groupby(["stop_name", "geometry_y"])
        .agg(avg_speed=("speed", "mean"))
        .reset_index()
        .rename(columns={"geometry_y": "geometry"})
    )
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
        get_line_color="""properties.avg_speed < 6 ? [255, 0, 0] : properties.avg_speed < 9 ? [255, 145, 0] : properties.avg_speed < 12 ? [255, 204, 0] : properties.avg_speed < 15 ? [144, 238, 144] : properties.avg_speed < 18 ? [50, 128, 50] : [0, 100, 0]""",
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
    st.pydeck_chart(deck)

    st.markdown(
        text.COLOR_BAR,
        unsafe_allow_html=True,
    )
