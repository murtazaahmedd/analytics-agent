select
    cast(id as bigint) as order_item_id,
    cast(order_id as bigint) as order_id,
    cast(user_id as bigint) as user_id,
    cast(product_id as bigint) as product_id,
    status,
    cast(created_at as timestamp) as created_at,
    cast(shipped_at as timestamp) as shipped_at,
    cast(delivered_at as timestamp) as delivered_at,
    cast(returned_at as timestamp) as returned_at,
    cast(sale_price as double) as sale_price
from {{ source('thelook', 'order_items') }}
qualify row_number() over (partition by id order by created_at desc) = 1
