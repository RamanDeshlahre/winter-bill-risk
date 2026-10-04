-- One row per day x Acorn group x tariff group: average usage alongside the weather.
-- Built for the Tableau dashboard (usage vs temperature over time).

with daily as (

    select * from {{ ref('stg_meter_readings_daily') }}
    where is_complete_day

),

households as (

    select household_id, acorn_group, tariff_group from {{ ref('dim_households') }}

),

weather as (

    select * from {{ ref('stg_weather_daily') }}

)

select
    d.reading_date,
    h.acorn_group,
    h.tariff_group,
    count(*)                            as households_reporting,
    avg(d.kwh_total)                    as avg_daily_kwh,
    max(w.temp_mean_c)                  as temp_mean_c,
    max(w.heating_degree_days)          as heating_degree_days
from daily d
inner join households h on d.household_id = h.household_id
left join weather w on d.reading_date = w.weather_date
group by 1, 2, 3
