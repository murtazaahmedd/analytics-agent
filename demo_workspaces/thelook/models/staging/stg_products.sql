select
    cast(id as bigint) as product_id,
    name as product_name,
    category,
    brand,
    department,
    cast(cost as double) as cost,
    cast(retail_price as double) as retail_price,
    cast(distribution_center_id as bigint) as distribution_center_id
from {{ source('thelook', 'products') }}
qualify row_number() over (partition by id order by id) = 1
