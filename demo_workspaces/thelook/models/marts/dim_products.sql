with products as (
    select * from {{ ref('stg_products') }}
),

centers as (
    select * from {{ ref('stg_distribution_centers') }}
)

select
    products.product_id,
    products.product_name,
    products.category,
    products.brand,
    products.department,
    products.cost,
    products.retail_price,
    centers.distribution_center_name as distribution_center
from products
left join centers on products.distribution_center_id = centers.distribution_center_id
