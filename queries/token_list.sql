DROP MATERIALIZED VIEW IF EXISTS dune_user_generated.cow_trusted_tokens;
CREATE MATERIALIZED VIEW dune_user_generated.cow_trusted_tokens (address) AS (
  SELECT *
  FROM (
      VALUES '{{TokenList}}'
    ) as _
);
select concat('0x', encode(contract_address, 'hex')) as address,
  symbol,
  decimals
from dune_user_generated.cow_trusted_tokens
  inner join erc20.tokens on contract_address = address