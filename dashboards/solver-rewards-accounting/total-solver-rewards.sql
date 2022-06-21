select
    r.accounting_period,
    execution_cost_eth,
    cow_rewards,
    realized_fees_eth
from solver_rewards r
join realized_fees f
    on r.accounting_period = f.accounting_period
