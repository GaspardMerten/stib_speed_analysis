from datetime import datetime, date, timedelta
from typing import List

import pandas as pd


def get_average_speed_for(client, line_id: str, points_tuple: List[str], min_date: date,
                          max_date: date, selected_days_index: List[int], start_hour: int, end_hour: int,
                          aggregation: str = "date_trunc('hour', {date})") -> pd.DataFrame:
    # selected days index is in human index, convert to database index (0 is sunday)
    selected_days = [i % 7 for i in selected_days_index]

    points = ", ".join(map(lambda x: f"'{x}'", points_tuple))

    query = f"""WITH entries AS (
        SELECT timestamp, unnest(data) as item
        FROM [table] 
        WHERE dayofweek(make_timestamp((timestamp+7200)*1000000)) IN ({', '.join(map(str, selected_days))}) AND hour(make_timestamp((timestamp+7200)*1000000)) >= {start_hour} AND hour(make_timestamp((timestamp+7200)*1000000)) <= {end_hour}
    ), filtered_entries AS (
        SELECT 
            *,
            ROW_NUMBER() OVER (PARTITION BY item.directionId, item.pointId, timestamp ORDER BY timestamp) as row_num
        FROM entries
        WHERE 
        item.lineId = '{line_id}' AND item.pointId IN ({points}) 
    ), deltaTable as (
    SELECT 
        timestamp,
        item.lineId as lineId,
        item.directionId as directionId,
        item.pointId as pointId,
        item.distanceFromPoint - lag(item.distanceFromPoint) OVER (PARTITION BY item.pointId, item.directionId,item.lineId ORDER BY timestamp) AS distance_delta,
        (timestamp - lag(timestamp) OVER (PARTITION BY item.pointId, item.directionId, item.lineId ORDER BY timestamp)) as time_delta
    FROM filtered_entries
    WHERE row_num = 1
    ), speedTable as (
    SELECT 
       timestamp,
        lineId,
        directionId,
        pointId,
        (distance_delta / time_delta) as speed
        FROM deltaTable
        WHERe time_delta < 40 AND distance_delta < 600
    )
    SELECT  lineId, directionId, pointId, avg(speed) * 3.6, count(*) as count, {aggregation.format(date="make_timestamp((timestamp+7200)*1000000)")} as agg
    FROM speedTable
    WHERE speed > 0 
    GROUP BY lineId, directionId, pointId, agg
    """

    results = client.advanced_query(
        "stib_vehicle_distance",
        query,
        datetime(min_date.year, min_date.month, min_date.day) - timedelta(hours=2),
        datetime(max_date.year, max_date.month, max_date.day) + pd.Timedelta(days=1) - timedelta(hours=2),
    )

    return pd.DataFrame.from_records(
        [x for x in results["results"]],
        columns=["lineId", "directionId", "pointId", "speed", "count", "date"]
    )
