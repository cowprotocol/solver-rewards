-- Can't use this if aggregate table has already been deleted:
-- select max(page) as last_page_number from dune_user_generated.cow_order_rewards_{{Environment}}
select max(replace(table_name, 'cow_order_rewards_{{Environment}}_page_', '')::numeric) as last_page
from INFORMATION_SCHEMA.views
where table_schema = 'dune_user_generated'
  and table_name ilike 'cow_order_rewards_{{Environment}}_page%';
