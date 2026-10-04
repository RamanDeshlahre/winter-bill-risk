-- One row per household that has smart meter data, with its attributes and data coverage.

with readings as (

    select * from {{ ref('stg_meter_readings_daily') }}

),

households as (

    select * from {{ ref('stg_households') }}

),

summary as (

    select
        household_id,
        min(reading_date)                                           as first_reading_date,
        max(reading_date)                                           as last_reading_date,
        count(*)                                                    as days_with_data,
        avg(case when is_complete_day then 1.0 else 0.0 end)        as share_complete_days,
        median(case when is_complete_day then kwh_total end)        as median_daily_kwh,
        avg(case when is_complete_day then kwh_total end)           as mean_daily_kwh
    from readings
    group by 1

)

select
    s.household_id,
    coalesce(h.acorn_group, 'Unknown')                              as acorn_group,
    h.acorn_category,
    coalesce(h.tariff_group, 'standard_flat')                       as tariff_group,
    s.first_reading_date,
    s.last_reading_date,
    s.days_with_data,
    s.share_complete_days,
    s.median_daily_kwh,
    s.mean_daily_kwh
from summary s
left join households h using (household_id)
