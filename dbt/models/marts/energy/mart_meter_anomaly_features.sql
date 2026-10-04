-- One row per household: signals that its meter readings look unusual.
-- These are NOT accusations. Low or zero usage can mean an empty home, a faulty or
-- disconnected meter, or (rarely) tampering/energy theft. The Python analysis turns
-- these signals into a prioritised review list with a "likely explanation" for each.

with expected as (

    select * from {{ ref('int_household_daily_expected') }}

),

readings as (

    select * from {{ ref('stg_meter_readings_daily') }}

),

households as (

    select * from {{ ref('dim_households') }}

),

daily_flags as (

    select
        household_id,
        reading_date,
        date_diff('day', date '2000-01-01', reading_date)           as day_number,
        kwh_total < 0.15 * median_daily_kwh                         as is_near_zero,
        usage_ratio_14d < 0.35                                      as is_sustained_low,
        usage_ratio_14d > 2.5                                       as is_sustained_high
    from expected

),

-- Stack the three signals so one "gaps and islands" query finds the longest run of
-- consecutive days for each signal.
flagged_days as (

    select household_id, 'near_zero' as signal, day_number
    from daily_flags where is_near_zero
    union all
    select household_id, 'sustained_low' as signal, day_number
    from daily_flags where is_sustained_low
    union all
    select household_id, 'sustained_high' as signal, day_number
    from daily_flags where is_sustained_high

),

islands as (

    select
        household_id,
        signal,
        day_number - row_number() over (
            partition by household_id, signal order by day_number
        )                                                           as island_id
    from flagged_days

),

runs as (

    select household_id, signal, count(*) as run_days
    from islands
    group by household_id, signal, island_id

),

longest_runs as (

    select
        household_id,
        max(case when signal = 'near_zero'      then run_days end)  as longest_near_zero_run_days,
        max(case when signal = 'sustained_low'  then run_days end)  as longest_sustained_low_run_days,
        max(case when signal = 'sustained_high' then run_days end)  as longest_sustained_high_run_days
    from runs
    group by 1

),

data_gaps as (

    select
        household_id,
        max(gap_days)                                               as longest_data_gap_days,
        sum(gap_days)                                               as total_missing_days
    from (
        select
            household_id,
            date_diff(
                'day',
                lag(reading_date) over (partition by household_id order by reading_date),
                reading_date
            ) - 1                                                   as gap_days
        from readings
    ) as with_gaps
    group by 1

),

usage_profile as (

    select
        household_id,
        avg(kwh_total)                                              as mean_daily_kwh,
        stddev_samp(kwh_total) / nullif(avg(kwh_total), 0)          as daily_kwh_cv,
        avg(case when kwh_total < 0.15 * median_daily_kwh then 1.0 else 0.0 end)
                                                                    as share_near_zero_days,
        avg(kwh_max_halfhour)                                       as mean_peak_halfhour_kwh,
        any_value(fit_kwh_per_hdd)                                  as fit_kwh_per_hdd,
        any_value(fit_r2)                                           as fit_r2,
        min(usage_ratio_14d)                                        as min_usage_ratio_14d,
        max(usage_ratio_14d)                                        as max_usage_ratio_14d
    from expected
    group by 1

)

select
    h.household_id,
    h.acorn_group,
    h.tariff_group,
    h.first_reading_date,
    h.last_reading_date,
    h.days_with_data,
    h.share_complete_days,
    p.mean_daily_kwh,
    p.daily_kwh_cv,
    p.share_near_zero_days,
    p.mean_peak_halfhour_kwh,
    p.fit_kwh_per_hdd,
    p.fit_r2,
    p.min_usage_ratio_14d,
    p.max_usage_ratio_14d,
    coalesce(r.longest_near_zero_run_days, 0)                       as longest_near_zero_run_days,
    coalesce(r.longest_sustained_low_run_days, 0)                   as longest_sustained_low_run_days,
    coalesce(r.longest_sustained_high_run_days, 0)                  as longest_sustained_high_run_days,
    coalesce(g.longest_data_gap_days, 0)                            as longest_data_gap_days,
    coalesce(g.total_missing_days, 0)                               as total_missing_days,
    1 - h.share_complete_days                                       as share_partial_days
from households h
left join usage_profile p on h.household_id = p.household_id
left join longest_runs  r on h.household_id = r.household_id
left join data_gaps     g on h.household_id = g.household_id
