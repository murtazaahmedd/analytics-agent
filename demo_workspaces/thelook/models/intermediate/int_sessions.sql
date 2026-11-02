select
    session_id,
    any_value(user_id) as user_id,
    min(created_at) as session_start,
    any_value(browser) as browser,
    any_value(traffic_source) as traffic_source,
    count(*) as event_count,
    bool_or(event_type = 'cart') as has_cart,
    bool_or(event_type = 'purchase') as has_purchase
from {{ ref('stg_events') }}
group by session_id
