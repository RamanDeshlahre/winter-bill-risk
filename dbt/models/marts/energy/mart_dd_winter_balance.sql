-- Direct Debit simulation: one row per household per winter month (Oct 2013 - Feb 2014).
--
-- How suppliers typically work: a fixed monthly Direct Debit is set from the last
-- 12 months of usage (here Oct 2012 - Sep 2013), divided equally across the year.
-- Bills are higher in winter, so the account balance falls. This model tracks that
-- balance month by month. A negative balance means the customer is "in debit"
-- (owes money), which is where collections risk starts.

{% set baseline_start = "date '" ~ var('baseline_start') ~ "'" %}
{% set baseline_end   = "date '" ~ var('baseline_end')   ~ "'" %}
{% set winter_start   = "date '" ~ var('winter_start')   ~ "'" %}
{% set winter_end     = "date '" ~ var('winter_end')     ~ "'" %}

with monthly as (

    select * from {{ ref('fct_household_month') }}

),

baseline as (

    select
        household_id,
        count(*)                        as baseline_months,
        sum(complete_days)              as baseline_complete_days,
        sum(est_bill_gbp)               as baseline_annual_bill_gbp
    from monthly
    where month_start between {{ baseline_start }} and {{ baseline_end }}
    group by 1

),

winter as (

    select
        household_id,
        count(*)                        as winter_months,
        sum(complete_days)              as winter_complete_days
    from monthly
    where month_start between {{ winter_start }} and {{ winter_end }}
    group by 1

),

-- Only households with near-complete data in BOTH windows are analysed
eligible as (

    select
        b.household_id,
        b.baseline_annual_bill_gbp / 12.0   as direct_debit_gbp
    from baseline b
    inner join winter w on b.household_id = w.household_id
    where b.baseline_months = 12
      and b.baseline_complete_days >= {{ var('min_coverage') }}
            * (date_diff('day', {{ baseline_start }}, {{ baseline_end }}) + 1)
      and w.winter_months = date_diff('month', {{ winter_start }}, {{ winter_end }}) + 1
      and w.winter_complete_days >= {{ var('min_coverage') }}
            * (date_diff('day', {{ winter_start }}, {{ winter_end }}) + 1)

),

balance_path as (

    select
        m.household_id,
        m.acorn_group,
        m.tariff_group,
        m.month_start,
        row_number() over (
            partition by m.household_id order by m.month_start
        )                                               as month_number,
        e.direct_debit_gbp,
        m.est_bill_gbp,
        e.direct_debit_gbp - m.est_bill_gbp             as monthly_surplus_gbp,
        sum(e.direct_debit_gbp - m.est_bill_gbp) over (
            partition by m.household_id
            order by m.month_start
            rows between unbounded preceding and current row
        )                                               as account_balance_gbp
    from monthly m
    inner join eligible e on m.household_id = e.household_id
    where m.month_start between {{ winter_start }} and {{ winter_end }}

)

select
    household_id || '_' || strftime(month_start, '%Y-%m')  as household_month_id,
    *,
    account_balance_gbp < 0                                 as is_in_debit
from balance_path
