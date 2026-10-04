-- One row per credit customer with payment-behaviour features for the early-warning model.
-- Payment ratios compare the amount paid in month k with the bill issued the month
-- before (k+1), because a bill is paid the month after it is issued.

with customers as (

    select * from {{ ref('stg_credit_customers') }}

)

select
    customer_id,
    credit_limit,
    sex,
    education,
    marital_status,
    age,
    case when age < 30 then '21-29'
         when age < 40 then '30-39'
         when age < 50 then '40-49'
         else '50+' end                                                 as age_band,

    -- Lateness
    (case when pay_status_m1 >= 1 then 1 else 0 end
     + case when pay_status_m2 >= 1 then 1 else 0 end
     + case when pay_status_m3 >= 1 then 1 else 0 end
     + case when pay_status_m4 >= 1 then 1 else 0 end
     + case when pay_status_m5 >= 1 then 1 else 0 end
     + case when pay_status_m6 >= 1 then 1 else 0 end)                  as months_late_6m,
    greatest(pay_status_m1, pay_status_m2, pay_status_m3,
             pay_status_m4, pay_status_m5, pay_status_m6, 0)            as max_months_late_6m,
    greatest(pay_status_m1, 0)                                          as months_late_now,
    greatest(pay_status_m1, 0) - greatest(pay_status_m3, 0)             as late_trend_3m,
    case when pay_status_m1 >= 1 and pay_status_m2 >= 1 and pay_status_m3 >= 1 then 3
         when pay_status_m1 >= 1 and pay_status_m2 >= 1 then 2
         when pay_status_m1 >= 1 then 1
         else 0 end                                                     as consecutive_late_months,
    (case when pay_status_m1 = -1 then 1 else 0 end
     + case when pay_status_m2 = -1 then 1 else 0 end
     + case when pay_status_m3 = -1 then 1 else 0 end
     + case when pay_status_m4 = -1 then 1 else 0 end
     + case when pay_status_m5 = -1 then 1 else 0 end
     + case when pay_status_m6 = -1 then 1 else 0 end)                  as months_paid_in_full_6m,

    -- Balance and utilisation
    bill_amt_m1 / nullif(credit_limit, 0)                               as utilisation_now,
    (bill_amt_m1 + bill_amt_m2 + bill_amt_m3
     + bill_amt_m4 + bill_amt_m5 + bill_amt_m6) / 6.0
        / nullif(credit_limit, 0)                                       as avg_utilisation_6m,
    (bill_amt_m1 - bill_amt_m3) / nullif(credit_limit, 0)               as bill_growth_3m,

    -- How much of each bill was actually paid (capped at 2x; 1 when nothing was owed)
    case when bill_amt_m2 > 0 then least(paid_amt_m1 / bill_amt_m2, 2) else 1 end
                                                                        as pay_ratio_m1,
    (  case when bill_amt_m2 > 0 then least(paid_amt_m1 / bill_amt_m2, 2) else 1 end
     + case when bill_amt_m3 > 0 then least(paid_amt_m2 / bill_amt_m3, 2) else 1 end
     + case when bill_amt_m4 > 0 then least(paid_amt_m3 / bill_amt_m4, 2) else 1 end
     + case when bill_amt_m5 > 0 then least(paid_amt_m4 / bill_amt_m5, 2) else 1 end
     + case when bill_amt_m6 > 0 then least(paid_amt_m5 / bill_amt_m6, 2) else 1 end
    ) / 5.0                                                             as avg_pay_ratio_5m,
    (  case when bill_amt_m2 > 0 and paid_amt_m1 = 0 then 1 else 0 end
     + case when bill_amt_m3 > 0 and paid_amt_m2 = 0 then 1 else 0 end
     + case when bill_amt_m4 > 0 and paid_amt_m3 = 0 then 1 else 0 end
     + case when bill_amt_m5 > 0 and paid_amt_m4 = 0 then 1 else 0 end
     + case when bill_amt_m6 > 0 and paid_amt_m5 = 0 then 1 else 0 end
    )                                                                   as months_no_payment_5m,

    -- Raw history kept for transparency
    pay_status_m1, pay_status_m2, pay_status_m3,
    pay_status_m4, pay_status_m5, pay_status_m6,
    bill_amt_m1, bill_amt_m2, paid_amt_m1,

    defaulted_next_month
from customers
