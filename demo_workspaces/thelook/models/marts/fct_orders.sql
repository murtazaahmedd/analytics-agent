select
    order_id,
    user_id,
    status,
    created_at,
    num_of_items,
    status = 'Cancelled' as is_cancelled,
    row_number() over (partition by user_id order by created_at, order_id) = 1 as is_first_order
from {{ ref('stg_orders') }}
