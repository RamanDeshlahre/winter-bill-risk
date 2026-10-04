-- Weather-adjusted expected usage for every complete household-day.
-- For each household we fit: daily kWh = a + b * heating_degree_days (least squares,
-- using the household's full history). The usage_ratio compares actual with expected
-- usage, so a cold-weather rise is not mistaken for an anomaly and a summer dip is not
-- mistaken for a meter problem.

with daily as (

    select household_id, reading_date, kwh_total, kwh_max_halfhour
    from {{ ref('stg_meter_readings_daily') }}
    where is_complete_day

),

weather as (

    select weather_date, heating_degree_days, temp_mean_c
    from {{ ref('stg_weather_daily') }}

),

joined as (

    select d.*, w.heating_degree_days, w.temp_mean_c
    from daily d
    left join weather w on d.reading_date = w.weather_date

),

fit as (

    select
        household_id,
        regr_intercept(kwh_total, heating_degree_days)  as fit_intercept_kwh,
        regr_slope(kwh_total, heating_degree_days)      as fit_kwh_per_hdd,
        regr_r2(kwh_total, heating_degree_days)         as fit_r2,
        median(kwh_total)                               as median_daily_kwh
    from joined
    group by 1

),

scored as (

    select
        j.*,
        f.fit_kwh_per_hdd,
        f.fit_r2,
        f.median_daily_kwh,
        -- floor of 0.1 kWh avoids dividing by ~0 for very low users
        greatest(f.fit_intercept_kwh + f.fit_kwh_per_hdd * j.heating_degree_days, 0.1)
                                                        as expected_kwh
    from joined j
    inner join fit f using (household_id)

)

select
    *,
    kwh_total / expected_kwh                            as usage_ratio,
    avg(kwh_total / expected_kwh) over (
        partition by household_id
        order by reading_date
        range between interval 13 days preceding and current row
    )                                                   as usage_ratio_14d
from scored
