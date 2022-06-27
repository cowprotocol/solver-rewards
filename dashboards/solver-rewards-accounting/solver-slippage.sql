select
    solver_address, 
    solver_name, 
    usd_value, 
    eth_slippage_wei / 10^18 eth_slippage
from results
order by usd_value
