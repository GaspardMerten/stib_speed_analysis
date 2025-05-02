import json
import logging
from datetime import datetime
from enum import Enum
from typing import List

import duckdb
import pandas as pd
import requests
import requests.utils


def auth_request(*args, **kwargs):
    return requests.get(
        *args,
        **kwargs,
        headers={
            "Authorization": f"Bearer 42227799ae2e74ebc42ca66dee38f4352456c2e93a21962133e0056fd228392eecd70222df0a0c3882438acdfb59de933c50ef368cebb8f5ab8b19d3bd8d2134"
        },
    )


class SpeedComputationMode(Enum):
    GREATER_THAN_ZERO = 1
    GREATER_THAN_ZERO_IF_CLOSE_TO_STOP = 2
    ALL = 3


MAPPING_SPEED_COMPUTATION_MODE = {
    SpeedComputationMode.GREATER_THAN_ZERO: "speed > 0",
    SpeedComputationMode.GREATER_THAN_ZERO_IF_CLOSE_TO_STOP: "distanceFromPoint > 50 or speed > 0",
    SpeedComputationMode.ALL: "speed >= 0",
}


def get_average_speed_for(
    line_id: str,
    points_tuple: List[str],
    start_date: datetime,
    end_date: datetime,
    excluded_periods: List[tuple[datetime, datetime]],
    selected_days_index: List[int],
    start_hour: int,
    end_hour: int,
    speed_computation_mode: SpeedComputationMode = SpeedComputationMode.ALL,
) -> pd.DataFrame:
    # selected days index is in human index, convert to database index (0 is sunday)
    selected_days = [i % 7 for i in selected_days_index]

    points = ", ".join(map(lambda x: f"'{x}'", points_tuple))

    start_datetime = datetime(
        start_date.year, start_date.month, start_date.day, start_hour
    )
    end_datetime = datetime(end_date.year, end_date.month, end_date.day, end_hour, 59)

    # Convert to EU timezone

    min_date_utc = int(start_datetime.timestamp())
    max_date_utc = int(end_datetime.timestamp())

    keys = {"lineId": line_id}
    keys_url = requests.utils.quote(json.dumps(keys))
    response = auth_request(
        f"https://api.mobilitytwin.brussels/parquetized?start_timestamp={min_date_utc}&end_timestamp={max_date_utc}&component=stib_vehicle_distance_parquetize&keys={keys_url}"
    ).json()

    logging.info(f"{start_datetime}, {end_datetime}, {min_date_utc}, {max_date_utc}")

    WHERE_FOR_DATE_AND_EXCLUDED_PERIODS = (
        f"(local_date >= '{start_datetime}' AND local_date <= '{end_datetime}')"
    )

    if excluded_periods:
        WHERE_FOR_DATE_AND_EXCLUDED_PERIODS += " AND "
        WHERE_FOR_DATE_AND_EXCLUDED_PERIODS += " AND ".join(
            [
                f"(local_date < '{start}' OR datetrunc( 'day',local_date) > '{end}')"
                for start, end in excluded_periods
            ]
        )

    parquet_files = ",".join(map(lambda x: f"'{x}'", response["results"]))

    query = f"""WITH entries AS (   
        SELECT lineId,pointId,directionId,distanceFromPoint, (date AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Brussels')::timestamp as local_date
        FROM read_parquet([{parquet_files}])
        WHERE lineId = '{line_id}' AND pointId IN ({points}) AND
        extract(hour from local_date) >= {start_hour} AND extract(hour from local_date) <= {end_hour} 
        AND extract(dow from local_date) IN ({', '.join(map(str, selected_days))}) 
        AND {WHERE_FOR_DATE_AND_EXCLUDED_PERIODS}  

    ), filtered_entries AS (
        SELECT 
            *,
            count(*) OVER (PARTITION BY directionId, pointId, local_date) as row_count
        FROM entries
    ), deltaTable as (
    SELECT 
        local_date,
        lineId as lineId,
        directionId as directionId,
        pointId as pointId,
        distanceFromPoint as distanceFromPoint,
        distanceFromPoint - lag(distanceFromPoint) OVER (PARTITION BY pointId, directionId,lineId ORDER BY local_date) AS distance_delta,
        (local_date - lag(local_date) OVER (PARTITION BY pointId, directionId, lineId ORDER BY local_date)) as time_delta
    FROM filtered_entries
    WHERE row_count = 1
    ), speedTable as (
    SELECT 
       local_date,
        lineId,
        directionId,
        pointId,
        distanceFromPoint,
        (distance_delta / epoch(time_delta)) as speed
        FROM deltaTable
        WHERe epoch(time_delta) < 30 AND distance_delta < 600
    )
    SELECT  lineId, directionId, pointId, avg(speed) * 3.6, count(*) as count, time_bucket(interval '15 minutes', local_date) as agg
    FROM speedTable
    WHERE {MAPPING_SPEED_COMPUTATION_MODE[speed_computation_mode]}
    GROUP BY lineId, directionId, pointId, agg
    """
    con = duckdb.connect()
    results_df = con.execute(query).df()
    columns = ["lineId", "directionId", "pointId", "speed", "count", "date"]
    results_df.columns = columns
    results_df.to_csv("results.csv", index=False)
    return results_df
