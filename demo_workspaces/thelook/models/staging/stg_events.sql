select
    cast(id as bigint) as event_id,
    cast(user_id as bigint) as user_id,
    session_id,
    cast(sequence_number as integer) as sequence_number,
    cast(created_at as timestamp) as created_at,
    browser,
    traffic_source,
    uri,
    event_type
from {{ source('thelook', 'events') }}
qualify row_number() over (partition by id order by created_at desc) = 1
