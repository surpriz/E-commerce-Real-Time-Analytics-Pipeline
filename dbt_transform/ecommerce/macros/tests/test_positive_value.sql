# dbt_transform/ecommerce/macros/tests/test_positive_value.sql
{% test positive_value(model, column_name) %}

SELECT *
FROM {{ model }}
WHERE {{ column_name }} <= 0
   OR {{ column_name }} IS NULL

{% endtest %}