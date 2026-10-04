-- Fails if a household's final winter balance does not equal
-- total Direct Debit paid minus total bills (to the penny).

with last_month as (
    select household_id, account_balance_gbp
    from {{ ref('mart_dd_winter_balance') }}
    qualify row_number() over (partition by household_id order by month_start desc) = 1
),

totals as (
    select household_id, sum(direct_debit_gbp) - sum(est_bill_gbp) as expected_balance_gbp
    from {{ ref('mart_dd_winter_balance') }}
    group by 1
)

select l.household_id, l.account_balance_gbp, t.expected_balance_gbp
from last_month l
inner join totals t on l.household_id = t.household_id
where abs(l.account_balance_gbp - t.expected_balance_gbp) > 0.01
