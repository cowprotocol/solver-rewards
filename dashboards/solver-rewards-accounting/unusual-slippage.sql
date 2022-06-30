select
    block_time,
    rpt.solver_name,
    concat('0x', encode(rpt.tx_hash, 'hex')) as tx_hash,
    usd_value,
    batch_value,
    100 * usd_value / batch_value as relative_slippage
from results_per_tx rpt
join gnosis_protocol_v2."batches" b
    on rpt.tx_hash = b.tx_hash
where (
    abs(usd_value) > '{{MinAbsoluteSlippageTolerance}}'
    and
    100.0 * abs(usd_value) / batch_value > '{{RelativeSlippageTolerance}}'
) or
    abs(usd_value) > '{{SignificantSlippageValue}}'
order by relative_slippage
