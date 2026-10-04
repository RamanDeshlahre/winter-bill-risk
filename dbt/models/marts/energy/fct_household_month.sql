-- One row per household per month: usage and the bill it would cost at today's prices.
-- Monthly usage is estimated from the average of *complete* days, multiplied by the
-- number of days in the month, so a few missing days don't make a month look cheap.

with daily as (

    select * from {{ ref('stg_meter_readings_daily') }}
    where is_complete_day

),

weather as (

    select * from {{ ref('stg_weather_daily') }}

),

households as (

    select household_id, acorn_group, tariff_group from {{ ref('dim_households') }}

),

monthly_usage as (

    select
        household_id,
        cast(date_trunc('month', reading_date) as date)             as month_start,
        count(*)                                                    as complete_days,
        avg(kwh_total)                                              as avg_daily_kwh
    from daily
    group by 1, 2

),

monthly_weather as (

    select
        cast(date_trunc('month', weather_date) as date)             as month_start,
        avg(temp_mean_c)                                            as avg_temp_c,
        sum(heating_degree_days)                                    as heating_degree_days
    from weather
    group by 1

),

combined as (

    select
        u.household_id,
        h.acorn_group,
        h.tariff_group,
        u.month_start,
        day(last_day(u.month_start))                                as days_in_month,
        u.complete_days,
        u.avg_daily_kwh,
        w.avg_temp_c,
        w.heating_degree_days
    from monthly_usage u
    left join households h on u.household_id = h.household_id
    left join monthly_weather w on u.month_start = w.month_start

)

select
    household_id || '_' || strftime(month_start, '%Y-%m')          as household_month_id,
    household_id,
    acorn_group,
    tariff_group,
    month_start,
    days_in_month,
    complete_days,
    complete_days * 1.0 / days_in_month                             as coverage,
    avg_daily_kwh,
    avg_daily_kwh * days_in_month                                   as est_month_kwh,
    days_in_month * (
        avg_daily_kwh * {{ var('unit_rate_gbp_per_kwh') }}
        + {{ var('standing_charge_gbp_per_day') }}
    )                                                               as est_bill_gbp,
    avg_temp_c,
    heating_degree_days
from combined
