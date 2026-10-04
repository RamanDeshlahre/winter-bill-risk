-- One row per day of London weather (Dark Sky, via Kaggle).
--
-- DATA QUALITY FIX: the source timestamps are in UTC. During British Summer Time
-- every day is stored as 23:00 on the *previous* day (428 of 882 rows), so a plain
-- cast to date shifts all summer weather back by one day and creates 3 duplicate
-- dates around the clock change. Adding one hour before casting puts every row on
-- its correct local date (882 unique, gap-free days).

with source as (

    select *
    from read_csv_auto(
        '{{ var("raw_path") }}/smart_meters/weather_daily_darksky.csv',
        header = true
    )

),

cleaned as (

    select
        cast(cast("time" as timestamp) + interval 1 hour as date)   as weather_date,
        cast(temperatureMax as double)                              as temp_max_c,
        cast(temperatureMin as double)                              as temp_min_c,
        cast(humidity as double)                                    as humidity,
        cast(windSpeed as double)                                   as wind_speed,
        summary                                                     as weather_summary
    from source

)

select
    *,
    (temp_max_c + temp_min_c) / 2.0                                 as temp_mean_c,
    greatest({{ var("hdd_base_temp_c") }} - (temp_max_c + temp_min_c) / 2.0, 0)
                                                                    as heating_degree_days
from cleaned
