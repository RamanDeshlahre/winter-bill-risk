-- One row per household per day of smart meter readings (Low Carbon London trial, via Kaggle).
-- Source files: data/raw/smart_meters/block_*.csv (one file per block of ~50 households).

with source as (

    select *
    from read_csv_auto(
        '{{ var("raw_path") }}/smart_meters/block_*.csv',
        header = true,
        filename = true
    )

),

renamed as (

    select
        trim(LCLid)                                  as household_id,
        cast(day as date)                            as reading_date,
        cast(energy_sum as double)                   as kwh_total,
        cast(energy_mean as double)                  as kwh_mean_halfhour,
        cast(energy_max as double)                   as kwh_max_halfhour,
        cast(energy_min as double)                   as kwh_min_halfhour,
        cast(energy_std as double)                   as kwh_std_halfhour,
        cast(energy_count as integer)                as halfhour_readings,
        regexp_extract(filename, 'block_[0-9]+')     as source_block
    from source

)

select
    household_id || '_' || strftime(reading_date, '%Y-%m-%d')   as reading_id,
    *,
    -- A complete day has all 48 half-hourly readings. Partial days (~1%) are
    -- excluded from usage averages so they don't look like low consumption.
    (halfhour_readings = 48 and kwh_total is not null)          as is_complete_day
from renamed
