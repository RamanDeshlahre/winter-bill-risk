-- Fails if any meter reading is negative (physically impossible for these meters).
select reading_id, kwh_total
from {{ ref('stg_meter_readings_daily') }}
where kwh_total < 0 or kwh_min_halfhour < 0
