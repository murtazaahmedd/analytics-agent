with items as (
    select * from {{ ref('stg_order_items') }}
),

products as (
    select * from {{ ref('stg_products') }}
)

select
    items.*,
    products.cost,
    products.category,
    products.brand,
    products.distribution_center_id,
    items.status = 'Cancelled' as is_cancelled,
    items.status = 'Returned' as is_returned,
    items.delivered_at is not null as is_delivered
from items
left join products on items.product_id = products.product_id
