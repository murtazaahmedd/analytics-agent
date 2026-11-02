select
    order_item_id,
    order_id,
    user_id,
    product_id,
    status,
    created_at,
    shipped_at,
    sale_price,
    cost,
    is_cancelled,
    is_returned,
    is_delivered,
    case when not is_cancelled then sale_price else 0 end as gross_revenue_amount,
    case when is_returned then sale_price else 0 end as returned_revenue_amount,
    case when not is_cancelled then sale_price - cost else 0 end as margin_amount,
    case when not is_cancelled then 1 else 0 end as is_sold,
    date_diff('second', created_at, shipped_at) / 3600.0 as hours_to_ship
from {{ ref('int_order_lines_enriched') }}
