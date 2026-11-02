select
    user_id,
    cast(date_trunc('month', created_at) as date) as order_month,
    count(*) as orders_in_month,
    count(*) >= 2 as is_repeat
from {{ ref('stg_orders') }}
where status != 'Cancelled'
group by 1, 2
