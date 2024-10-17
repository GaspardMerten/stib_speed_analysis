from datetime import datetime, timezone, timedelta
from enum import Enum
from io import BytesIO
from typing import List

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

# TODO: download all files matching before, then query them all at once

def auth_request(*args, **kwargs):
    return requests.get(*args, **kwargs, headers={
        "Authorization": f"Bearer 42227799ae2e74ebc42ca66dee38f4352456c2e93a21962133e0056fd228392eecd70222df0a0c3882438acdfb59de933c50ef368cebb8f5ab8b19d3bd8d2134"})


class SpeedComputationMode(Enum):
    GREATER_THAN_ZERO = 1
    GREATER_THAN_ZERO_IF_CLOSE_TO_STOP = 2
    ALL = 3


MAPPING_SPEED_COMPUTATION_MODE = {
    SpeedComputationMode.GREATER_THAN_ZERO: "speed > 0",
    SpeedComputationMode.GREATER_THAN_ZERO_IF_CLOSE_TO_STOP: "distanceFromPoint > 50 or speed > 0",
    SpeedComputationMode.ALL: "speed >= 0"
}


def get_average_speed_for(line_id: str, points_tuple: List[str], date: datetime,
                          selected_days_index: List[int], start_hour: int, end_hour: int,
                          aggregation: str = "date_trunc('hour', {date})",
                          speed_computation_mode: SpeedComputationMode = SpeedComputationMode.ALL) -> pd.DataFrame:
    # selected days index is in human index, convert to database index (0 is sunday)
    selected_days = [i % 7 for i in selected_days_index]

    points = ", ".join(map(lambda x: f"'{x}'", points_tuple))

    min_date_utc = int(datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp())
    max_date_utc = int((datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc) + timedelta(
        days=1) - timedelta(seconds=1)).timestamp())
    print(datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc) + timedelta(
        days=1))
    response = auth_request(
        f"https://api.mobilitytwin.brussels/parquetized?start_timestamp={min_date_utc}&end_timestamp={max_date_utc}&component=stib_vehicle_distance_parquetize"
    ).json()
    print(f"https://api.mobilitytwin.brussels/parquetized?start_timestamp={min_date_utc}&end_timestamp={max_date_utc}&component=stib_vehicle_distance_parquetize")
    arrow_table = None
    print(len(response["results"]))
    print(response["results"])
    for url in response["results"]:
        data = BytesIO(requests.get(url).content)
        if arrow_table is None:
            arrow_table = pq.read_table(data)
        else:
            arrow_table = pa.concat_tables([arrow_table, pq.read_table(data)])
    print("finished")
    query = f"""WITH entries AS (
        SELECT epoch(date)::int as timestamp, unnest(data) as item
        FROM arrow_table 
        WHERE timestamp >= {min_date_utc} AND timestamp <= {max_date_utc} AND extract(dow from date) in ({', '.join(map(str, selected_days))}) AND extract(hour from date) >= {start_hour} AND extract(hour from date) <= {end_hour}
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
        item.distanceFromPoint as distanceFromPoint,
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
        distanceFromPoint,
        (distance_delta / time_delta) as speed
        FROM deltaTable
        WHERe time_delta < 40 AND distance_delta < 600
    )
    SELECT  lineId, directionId, pointId, avg(speed) * 3.6, count(*) as count, {aggregation.format(date="make_timestamp((timestamp::bigint*1000000))")} as agg
    FROM speedTable
    WHERE {MAPPING_SPEED_COMPUTATION_MODE[speed_computation_mode]}
    GROUP BY lineId, directionId, pointId, agg
    """

    con = duckdb.connect()
    results = con.execute(query).df()
    print(results)
    columns = ["lineId", "directionId", "pointId", "speed", "count", "date"]
    results.columns = columns
    # convert date to local timezone (first set timezone to UTC, then convert to local timezone)
    results["date"] = pd.to_datetime(results["date"]).dt.tz_localize("UTC").dt.tz_convert("Europe/Brussels")

    return results
