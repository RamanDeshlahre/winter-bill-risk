-- One row per household in the Direct Debit simulation: how far into debit it went
-- this winter, plus features that were already known in October (from the baseline
-- year) for the early-warning analysis.

{% set baseline_start = "date '" ~ var('baseline_start') ~ "'" %}
{% set baseline_end   = "date '" ~ var('baseline_end')   ~ "'" %}

with balance as (

    select * from {{ ref('mart_dd_winter_balance') }}

),

monthly as (

    select * from {{ ref('fct_household_month') }}
    where month_start between {{ baseline_start }} and {{ baseline_end }}
      and household_id in (select distinct household_id from balance)

),

households as (

    select * from {{ ref('dim_households') }}

),

winter_outcome as (

    select
        household_id,
        max(direct_debit_gbp)                                       as direct_debit_gbp,
        sum(est_bill_gbp)                                           as winter_bills_gbp,
        sum(direct_debit_gbp)                                       as winter_dd_paid_gbp,
        greatest(-min(account_balance_gbp), 0)                      as peak_debt_gbp,
        sum(case when is_in_debit then 1 else 0 end)                as months_in_debit
    from balance
    group by 1

),

baseline_features as (

    select
        household_id,
        sum(est_month_kwh)                                          as baseline_annual_kwh,
        avg(case when month(month_start) in (12, 1, 2) then avg_daily_kwh end)
                                                                    as baseline_winter_daily_kwh,
        avg(case when month(month_start) in (6, 7, 8) then avg_daily_kwh end)
                                                                    as baseline_summer_daily_kwh,
        sum(case when month(month_start) in (10, 11, 12, 1, 2) then est_month_kwh else 0 end)
            / nullif(sum(est_month_kwh), 0)                         as baseline_oct_feb_kwh_share,
        regr_slope(avg_daily_kwh, heating_degree_days / days_in_month)
                                                                    as baseline_kwh_per_hdd,
        stddev_samp(avg_daily_kwh) / nullif(avg(avg_daily_kwh), 0)  as baseline_monthly_cv,
        sum(case when month(month_start) in (10, 11, 12, 1, 2) then est_bill_gbp else 0 end)
                                                                    as prior_winter_bills_gbp
    from monthly
    group by 1

),

-- "Seasonality only" view: if the Direct Debit had perfectly matched the baseline
-- year's total, how deep would the winter dip still have been?
seasonal_dd as (

    select
        household_id,
        month_start,
        est_bill_gbp,
        sum(est_bill_gbp) over (partition by household_id) / 12.0  as perfect_dd_gbp
    from monthly

),

seasonal_path as (

    select
        household_id,
        sum(perfect_dd_gbp - est_bill_gbp) over (
            partition by household_id
            order by month_start
            rows between unbounded preceding and current row
        )                                                           as cumulative_balance_gbp
    from seasonal_dd

),

seasonal_only as (

    select
        household_id,
        greatest(-min(cumulative_balance_gbp), 0)                   as seasonal_only_peak_debt_gbp
    from seasonal_path
    group by 1

)

select
    o.household_id,
    h.acorn_group,
    h.acorn_category,
    h.tariff_group,
    o.direct_debit_gbp,
    o.winter_bills_gbp,
    o.winter_dd_paid_gbp,
    o.peak_debt_gbp,
    o.peak_debt_gbp / o.direct_debit_gbp                            as peak_debt_in_months_of_dd,
    o.months_in_debit,
    o.peak_debt_gbp / o.direct_debit_gbp >= {{ var('at_risk_debt_months') }}
                                                                    as is_at_risk,
    f.baseline_annual_kwh,
    f.baseline_winter_daily_kwh,
    f.baseline_summer_daily_kwh,
    f.baseline_winter_daily_kwh / nullif(f.baseline_summer_daily_kwh, 0)
                                                                    as baseline_winter_summer_ratio,
    f.baseline_oct_feb_kwh_share,
    f.baseline_kwh_per_hdd,
    f.baseline_monthly_cv,
    f.prior_winter_bills_gbp,
    o.winter_bills_gbp / nullif(f.prior_winter_bills_gbp, 0) - 1    as winter_bill_change_vs_prior_winter,
    s.seasonal_only_peak_debt_gbp
from winter_outcome o
inner join households h on o.household_id = h.household_id
inner join baseline_features f on o.household_id = f.household_id
inner join seasonal_only s on o.household_id = s.household_id
