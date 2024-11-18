HEADER = """
# 🚌 STIB Speed Analysis Dashboard

Welcome to the **STIB Speed Analysis Dashboard**, a powerful tool developed in collaboration with the CoDE lab at the Université Libre de Bruxelles as part of the Brussels Mobility Twin project. This dashboard provides a user-friendly interface to analyze the speed of STIB vehicles across different lines and directions over specific time periods.

With this dashboard, you can:
- Select a line and direction to focus your analysis.
- Filter data by time periods, days of the week, and even exclude certain periods like holidays.
- Visualize results with detailed data tables and dynamic plots, offering insights into vehicle speeds at different times and stops.

### 📃 Features:
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
            <li><strong>Speed >= 0</strong>: (VICOM) This mode will include all the results where the speed is greater or equal to 0.</li>
            <li><strong>Speed >= 0 but not 0 if close to stop</strong>: (VICOM without time at stop)    This mode will include all the results where the speed is greater or equal to 0, but not 0 if the stop is close to the stop.</li>
            <li><strong>Speed > 0</strong>: This mode will include all the results where the speed is greater than 0.</li>
        </ul>
        The first one is the most pessimistic, the last one is the most optimistic.<br><br>
        
    <details style="margin-bottom: 20px">
    <summary style="font-weight: bold; font-size: 1rem">Methodology details</summary>
    <p>
        Unlike De Lijn, TEC, and most other public transport systems using the GTFS-RealTime format 
        (accessible via Google Maps), STIB does not provide open-access data on vehicle speed or 
        detailed position tracking. Instead, STIB supplies only the distance in meters from the last stop 
        for each vehicle every 20 seconds, without vehicle identifiers.
    </p>

    <h4>Calculating Speed</h4>
    <p>
        Due to the absence of identifiers, speed can only be calculated under specific conditions:
    </p>
    <ul>
        <li>A single bus must be present on a interstop at both <code>t=0s</code> and <code>t=20s</code>.</li>
        <li>The distance delta (change in distance) must be non-negative, ensuring it is not a new bus entering 
            or an existing one leaving the segment.</li>
    </ul>
    <p>
        Speed is then derived by dividing the distance delta by the time delta. While this approach reduces the 
        number of usable data points, using a 15-minute data window ensures consistent speed calculations across the STIB network.
    </p>

    <h4>Limitations and Opportunities</h4>
    <p>
        The lack of vehicle identifiers poses a significant limitation. If STIB provided identifiers, as many other 
        companies do without GDPR concerns, speed calculations could be significantly more accurate.
    </p>

    <h4>Interstop Speed Averaging</h4>
    <p>
        The last stop ID is used to assign a interstop to each point. This ID updates when the bus reaches the next stop. 
        However, because data arrives every 20 seconds, the same stop ID can appear for multiple points, causing minor 
        discrep ancies in speed calculations. These discrepancies average out over longer intervals, meaning the speed for 
        a interstop represents the average speed from when the bus arrives at the start stop to when it reaches the end stop.
    </p>
    <h4>No data for underground stops</h4>
    <p>
        Due to the lack of network coverage, no data is available for underground stops, or too little to apply the 
        previous explained methodology. Hence, metros, some trams, and occasional buses interstops are not included in 
        the analysis.
    </p>
        </details>
            
    """

COLOR_BAR = """<div style="display: flex; margin-y: 10px; width: 100%; height: 30px; border: 1px solid #000; border-radius: 5px; overflow: hidden;">
  <div style="flex: 1; background-color: rgb(255, 0, 0); display: flex; align-items: center; justify-content: center; color: white;">
    0-6
  </div>
  <div style="flex: 1; background-color: rgb(255, 145, 0); display: flex; align-items: center; justify-content: center; color: white;">
    6-9
  </div>
  <div style="flex: 1; background-color: rgb(255, 204, 0); display: flex; align-items: center; justify-content: center; color: black;">
    9-12
  </div>
  <div style="flex: 1; background-color: rgb(144, 238, 144); display: flex; align-items: center; justify-content: center; color: black;">
    12-15
  </div>
  
  <div style="flex: 1; background-color: rgb(50, 128, 50); display: flex; align-items: center; justify-content: center; color: white;">
    15-18
    </div>
  <div style="flex: 1; background-color: rgb(0, 100, 0); display: flex; align-items: center; justify-content: center; color: white;">
    >18
  </div>
</div>
"""

RAW_DATA = (
    "### Raw data\nThe first table displays for each hour, segment, and date, the number of points during that "
    "hour, the speed computed, and the time spent between two stops which is computed using the speed and the "
    "length of the interstop ."
)


FOCUS = "Here you can focus on a specific line and direction to analyze the speed of vehicles over a specific time period and specific interstops. You can also filter the data by time periods, days of the week, and exc  lude certain periods like holidays."
