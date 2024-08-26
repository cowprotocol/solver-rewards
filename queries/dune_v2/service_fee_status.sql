WITH
bonding_pools (pool, name, initial_funder) AS (
  SELECT from_hex(pool), name, from_hex(funder) FROM (
    VALUES {{BondingPoolData}}
  ) AS _ (pool, name, funder)
),

first_event_after_timestamp AS (
  SELECT MAX(number) FROM ethereum.blocks
  WHERE time > CAST('2024-08-20 00:00:00' AS timestamp) -- CIP-48 starts bonding pool timer at midnight UTC on 20/08/24
),

-- Step 1: Determine the first vouch to set the 'joined_on' timestamp
initial_vouches AS (
  SELECT RANK() OVER (
      PARTITION BY solver, bondingPool, sender
      ORDER BY evt_block_number ASC, evt_index ASC  -- Rank by earliest event
    ) AS rk,
    evt_block_number,
    evt_index,
    solver,
    cowRewardTarget,
    bondingPool,
    sender,
    True AS active
  FROM cow_protocol_ethereum.VouchRegister_evt_Vouch
  WHERE evt_block_number <= (SELECT * FROM first_event_after_timestamp)
    AND bondingPool IN (SELECT pool FROM bonding_pools)
    AND sender IN (SELECT initial_funder FROM bonding_pools)
),

-- Select the first event for `joined_on`
joined_on_data AS (
  SELECT
    iv.solver,
    iv.cowRewardTarget AS reward_target,
    iv.bondingPool AS pool,
    iv.evt_block_number,
    iv.evt_index,
    iv.rk,
    True AS active
  FROM initial_vouches iv
  WHERE iv.rk = 1
),

-- Step 2: Determine the latest vouch or invalidation to filter active solvers
latest_vouches AS (
  SELECT RANK() OVER (
      PARTITION BY solver, bondingPool, sender
      ORDER BY evt_block_number DESC, evt_index DESC  -- Rank by latest event
    ) AS rk,
    evt_block_number,
    evt_index,
    solver,
    cowRewardTarget,
    bondingPool,
    sender,
    CASE WHEN event_type = 'Vouch' THEN True ELSE False END AS active
  FROM (
      SELECT
        evt_block_number,
        evt_index,
        solver,
        cowRewardTarget,
        bondingPool,
        sender,
        'Vouch' AS event_type
      FROM cow_protocol_ethereum.VouchRegister_evt_Vouch
      WHERE evt_block_number <= (SELECT * FROM first_event_after_timestamp)
        AND bondingPool IN (SELECT pool FROM bonding_pools)
        AND sender IN (SELECT initial_funder FROM bonding_pools)

      UNION

      SELECT
        evt_block_number,
        evt_index,
        solver,
        NULL AS cowRewardTarget,  -- Invalidation does not have a reward target
        bondingPool,
        sender,
        'InvalidateVouch' AS event_type
      FROM cow_protocol_ethereum.VouchRegister_evt_InvalidateVouch
      WHERE evt_block_number <= (SELECT * FROM first_event_after_timestamp)
        AND bondingPool IN (SELECT pool FROM bonding_pools)
        AND sender IN (SELECT initial_funder FROM bonding_pools)
  ) AS unioned_events
),

valid_vouches AS (
  SELECT
    lv.solver,
    lv.cowRewardTarget AS reward_target,
    lv.bondingPool AS pool
  FROM latest_vouches lv
  WHERE lv.rk = 1 AND lv.active = TRUE -- Only include solvers that are active
),

-- Convert block number to timestamp for joined_on
joined_on AS (
  SELECT
    jd.solver,
    jd.reward_target,
    jd.pool,
    bp.name AS pool_name,
    b.time AS joined_on
  FROM joined_on_data jd
  JOIN ethereum.blocks b
    ON b.number = jd.evt_block_number
  JOIN bonding_pools bp
    ON jd.pool = bp.pool
),

-- Only keep solvers that are still active based on the latest vouch/invalidation
named_results AS (
  SELECT
    jd.solver,
    CONCAT(environment, '-', s.name) AS solver_name,
    jd.pool_name,
    jd.joined_on,
    date_diff('day', date(jd.joined_on), date(NOW())) AS days_in_pool,
    GREATEST(
      DATE_ADD('month', 6, jd.joined_on),  -- Add 6 month grace period to joined_on
      TIMESTAMP '2024-08-20 00:00:00'  -- Deadline for solvers that joined before CIP-48 was introduced
    ) AS expires
  FROM joined_on jd
  JOIN cow_protocol_ethereum.solvers s
    ON s.address = jd.solver
  JOIN valid_vouches vv
    ON vv.solver = jd.solver AND vv.pool = jd.pool
)

SELECT
  nr.solver,
  nr.solver_name,
  nr.pool_name,
  nr.joined_on,
  nr.days_in_pool,
  nr.expires,
  CASE
    WHEN NOW() > nr.expires THEN TRUE
    ELSE FALSE
  END AS service_fee
FROM named_results nr;
