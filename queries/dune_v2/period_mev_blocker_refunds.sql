SELECT
  solver_address as solver,
  name,
  sum(value) as refund_wei
FROM cow_protocol_ethereum.batches as batch
JOIN ethereum.blocks as b
  ON block_number = b.number
INNER JOIN ethereum.transactions as t
  ON b.number = t.block_number
  AND b.hash = t.block_hash
  AND "from" = miner
JOIN cow_protocol_ethereum.solvers
  ON "to" = address
WHERE b.time >= timestamp '{{StartTime}}'
AND b.time < timestamp '{{EndTime}}'
GROUP BY solver_address, name