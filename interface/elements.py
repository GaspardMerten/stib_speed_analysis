from typing import Any

import streamlit as st


def card_number(title: str, value: Any, legend: str = None):
    st.markdown(
        (
            "<div style='background-color: #f9f9f9; padding: 20px; border-radius: 10px; text-align: center;'>"
            f"<h2>{title}</h2>"
            f"<h1>{value:0.2f}</h1>" + (f"<p>{legend}</p>" if legend else "")
        )
        + "</div>",
        unsafe_allow_html=True,
    )
