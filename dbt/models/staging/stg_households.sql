-- One row per household: tariff group and Acorn socio-economic group.

with source as (

    select *
    from read_csv_auto(
        '{{ var("raw_path") }}/smart_meters/informations_households.csv',
        header = true
    )

)

select
    trim(LCLid)                                                     as household_id,
    case when stdorToU = 'ToU' then 'dynamic_tou'
         else 'standard_flat' end                                   as tariff_group,
    Acorn                                                           as acorn_category,
    case when Acorn_grouped in ('Affluent', 'Comfortable', 'Adversity')
         then Acorn_grouped else 'Unknown' end                      as acorn_group,
    file                                                            as source_block
from source
