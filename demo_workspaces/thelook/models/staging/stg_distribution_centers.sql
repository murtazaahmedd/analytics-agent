select
    cast(id as bigint) as distribution_center_id,
    name as distribution_center_name
from {{ source('thelook', 'distribution_centers') }}
