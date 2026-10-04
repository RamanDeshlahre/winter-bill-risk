-- One row per credit card customer (UCI "Default of Credit Card Clients", Taiwan, 2005).
-- Months are renamed so that m1 = most recent month (September) ... m6 = oldest (April).
-- pay_status codes: -2 = no balance, -1 = paid in full, 0 = minimum paid (revolving),
-- 1..9 = number of months the payment is late.

with source as (

    select *
    from read_csv_auto(
        '{{ var("raw_path") }}/credit/UCI_Credit_Card.csv',
        header = true
    )

)

select
    cast(ID as integer)                         as customer_id,
    cast(LIMIT_BAL as double)                   as credit_limit,
    case SEX when 1 then 'male' when 2 then 'female' end            as sex,
    case EDUCATION when 1 then 'graduate_school'
                   when 2 then 'university'
                   when 3 then 'high_school'
                   else 'other_or_unknown' end                      as education,
    case MARRIAGE when 1 then 'married'
                  when 2 then 'single'
                  else 'other_or_unknown' end                       as marital_status,
    cast(AGE as integer)                        as age,

    cast(PAY_0 as integer)  as pay_status_m1,
    cast(PAY_2 as integer)  as pay_status_m2,
    cast(PAY_3 as integer)  as pay_status_m3,
    cast(PAY_4 as integer)  as pay_status_m4,
    cast(PAY_5 as integer)  as pay_status_m5,
    cast(PAY_6 as integer)  as pay_status_m6,

    cast(BILL_AMT1 as double) as bill_amt_m1,
    cast(BILL_AMT2 as double) as bill_amt_m2,
    cast(BILL_AMT3 as double) as bill_amt_m3,
    cast(BILL_AMT4 as double) as bill_amt_m4,
    cast(BILL_AMT5 as double) as bill_amt_m5,
    cast(BILL_AMT6 as double) as bill_amt_m6,

    cast(PAY_AMT1 as double)  as paid_amt_m1,
    cast(PAY_AMT2 as double)  as paid_amt_m2,
    cast(PAY_AMT3 as double)  as paid_amt_m3,
    cast(PAY_AMT4 as double)  as paid_amt_m4,
    cast(PAY_AMT5 as double)  as paid_amt_m5,
    cast(PAY_AMT6 as double)  as paid_amt_m6,

    cast("default.payment.next.month" as integer)                   as defaulted_next_month
from source
