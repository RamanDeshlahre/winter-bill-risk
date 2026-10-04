-- Fails if any calendar day between the first and last weather date is missing.
-- (Before the timezone fix in stg_weather_daily, this test failed.)

with bounds as (
    select min(weather_date) as first_day, max(weather_date) as last_day
    from {{ ref('stg_weather_daily') }}
),

calendar as (
    select cast(unnest(generate_series(first_day, last_day, interval 1 day)) as date) as calendar_date
    from bounds
)

select c.calendar_date
from calendar c
left join {{ ref('stg_weather_daily') }} w on c.calendar_date = w.weather_date
where w.weather_date is null
