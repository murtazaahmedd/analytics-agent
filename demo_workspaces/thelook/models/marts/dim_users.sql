select
    user_id,
    age,
    gender,
    country,
    traffic_source,
    created_at
from {{ ref('stg_users') }}
