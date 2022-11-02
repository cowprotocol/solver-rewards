-- In order to drop a page, must drop any view or table which depending on it (i.e. cascade)
DROP VIEW IF EXISTS dune_user_generated.cow_order_rewards_{{Environment}}_page_{{Page}} CASCADE;
