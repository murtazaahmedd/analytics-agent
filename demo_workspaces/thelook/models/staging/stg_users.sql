select
    cast(id as bigint) as user_id,
    cast(age as integer) as age,
    gender,
    country,
    traffic_source,
    cast(created_at as timestamp) as created_at
from {{ source('thelook', 'users') }}
qualify row_number() over (partition by id order by created_at desc) = 1
