select *,
       usd_value / (select price from eth_price) * 10 ^ 18 as eth_slippage_wei
from {{ResultTable}} -- Should be results