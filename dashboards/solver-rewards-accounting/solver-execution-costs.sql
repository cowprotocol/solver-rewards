select
    solver_address, 
    concat(environment, '-', name) as solver_name, 
    execution_cost_eth, 
    (case when eth_penalty is null then 0 else eth_penalty end) as eth_penalty, 
    batches_settled,
    num_trades,
    cow_reward_target 
from per_solver_results
