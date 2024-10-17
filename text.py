HEADER = """
# 🚆 STIB Speed Analysis Dashboard

Welcome to the **STIB Speed Analysis Dashboard**, a powerful tool developed in collaboration with the CoDE lab at the Université Libre de Bruxelles as part of the Brussels Mobility Twin project. This dashboard provides a user-friendly interface to analyze the speed of STIB vehicles across different lines and directions over specific time periods.

With this dashboard, you can:
- Select a line and direction to focus your analysis.
- Filter data by time periods, days of the week, and even exclude certain periods like holidays.
- Visualize results with detailed data tables and dynamic plots, offering insights into vehicle speeds at different times and stops.

### 🚀 Features:
- **Real-time Data Analysis:** Use up-to-date mobility data from the Brussels Mobility Twin platform.
- **Flexible Filtering:** Customize your analysis by selecting lines, stops, and periods of interest.
- **Interactive Visualizations:** View average speeds, times between stops, and other key metrics through intuitive charts and maps.
- **Custom Speed Computation Modes:** Adjust how speeds are calculated to suit your analysis needs, from conservative to more optimistic estimates.

Visit the [Brussels Mobility Twin](https://mobilitytwin.brussels/) for more information on the data sources and the project behind this dashboard.

Use the controls on the left to get started, and uncover insights into the dynamics of urban mobility in Brussels.

*For any questions or feedback, please contact gaspard.merten@ulb.be*

---
"""

SPEED = """
    ---
     #### Speed computation mode
     <p>The speed computation mode is used to filter the results based on the speed computed. The speed is computed
     using the evolution of the distance from the last stop and the time between two consecutive points. This data is
     refreshed every 20 seconds, meaning some uncertainties can be present in the results, particularly when the
        vehicle is stopped. The following modes are available: </p>
        <ul>
            <li><strong>Speed >= 0</strong>: This mode will include all the results where the speed is greater or equal to 0.</li>
            <li><strong>Speed >= 0 but not 0 if close to stop</strong>: This mode will include all the results where the speed is greater or equal to 0, but not 0 if the stop is close to the stop.</li>
            <li><strong>Speed > 0</strong>: This mode will include all the results where the speed is greater than 0.</li>
        </ul>
        The first one is the most pessimistic, the last one is the most optimistic.<br><br>
    """

COLOR_BAR = """<div style="display: flex; width: 100%; height: 30px; border: 1px solid #000; border-radius: 5px; overflow: hidden;">
  <div style="flex: 1; background-color: rgb(255, 0, 0); display: flex; align-items: center; justify-content: center; color: white;">
    0-6: Red
  </div>
  <div style="flex: 1; background-color: rgb(139, 69, 0); display: flex; align-items: center; justify-content: center; color: white;">
    6-9: Dark Orange
  </div>
  <div style="flex: 1; background-color: rgb(255, 165, 0); display: flex; align-items: center; justify-content: center; color: black;">
    9-12: Orange
  </div>
  <div style="flex: 1; background-color: rgb(144, 238, 144); display: flex; align-items: center; justify-content: center; color: black;">
    12-18: Light Green
  </div>
  <div style="flex: 1; background-color: rgb(0, 100, 0); display: flex; align-items: center; justify-content: center; color: white;">
    >18: Dark Green
  </div>
</div>
"""

RAW_DATA = (
    "### Raw data\nThe first table displays for each hour, segment, and date, the number of points during that "
    "hour, the speed computed, and the time spent between two stops which is computed using the speed and the "
    "length of the interstop."
)
