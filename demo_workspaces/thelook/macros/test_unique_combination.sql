{% test dbt_utils_free_unique_combination(model, columns) %}
select {{ columns | join(', ') }}
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
