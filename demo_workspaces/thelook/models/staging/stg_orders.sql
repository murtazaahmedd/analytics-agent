select
    cast(order_id as bigint) as order_id,
    cast(user_id as bigint) as user_id,
    status,
    cast(created_at as timestamp) as created_at,
    cast(shipped_at as timestamp) as shipped_at,
    cast(delivered_at as timestamp) as delivered_at,
    cast(returned_at as timestamp) as returned_at,
    cast(num_of_item as integer) as num_of_items
from {{ source('thelook', 'orders') }}
qualify row_number() over (partition by order_id order by created_at desc) = 1
