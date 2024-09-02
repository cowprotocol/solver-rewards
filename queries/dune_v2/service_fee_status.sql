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

initial_vouches AS (
  SELECT RANK() OVER (
      PARTITION BY solver, bondingPool, sender
      ORDER BY evt_block_number ASC, evt_index ASC
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

latest_vouches AS (
  SELECT RANK() OVER (
      PARTITION BY solver, bondingPool, sender
      ORDER BY evt_block_number DESC, evt_index DESC
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
  WHERE lv.rk = 1 AND lv.active = TRUE
),

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

named_results AS (
  SELECT
    jd.solver,
    CONCAT(environment, '-', s.name) AS solver_name,
    jd.pool_name,
    jd.pool,
    jd.joined_on,
    date_diff('day', date(jd.joined_on), date(NOW())) AS days_in_pool
  FROM joined_on jd
  JOIN cow_protocol_ethereum.solvers s
    ON s.address = jd.solver
  JOIN valid_vouches vv
    ON vv.solver = jd.solver AND vv.pool = jd.pool
),

ranked_named_results AS (
  SELECT
    nr.solver,
    nr.solver_name,
    nr.pool_name,
    nr.pool,
    nr.joined_on,
    nr.days_in_pool,
    ROW_NUMBER() OVER (PARTITION BY nr.solver_name ORDER BY nr.joined_on DESC) AS rn,
    COUNT(*) OVER (PARTITION BY nr.solver_name) AS solver_name_count
  FROM named_results nr
),

filtered_named_results AS (
  SELECT
    rnr.solver,
    rnr.solver_name,
    CASE
      WHEN rnr.solver_name_count > 1 THEN 'Colocation'
      ELSE rnr.pool_name
    END AS pool_name,
    rnr.pool,
    rnr.joined_on,
    rnr.days_in_pool,
    CASE
      WHEN rnr.solver_name_count > 1 THEN DATE_ADD('month', 3, rnr.joined_on)  -- Add 3 month grace period for colocated solvers
      ELSE GREATEST(
              DATE_ADD('month', 6, rnr.joined_on),  -- Add 6 month grace period to joined_on for non colocated solvers
              TIMESTAMP '2024-08-20 00:00:00'  -- Introduction of CIP-48
      )
    END AS expires
  FROM ranked_named_results rnr
  WHERE rnr.rn = 1
)

SELECT
  fnr.solver,
  fnr.solver_name,
  fnr.pool_name,
  fnr.pool,
  fnr.joined_on,
  fnr.days_in_pool,
  CASE
    WHEN fnr.pool_name = 'Gnosis' THEN TIMESTAMP '2028-10-08 00:00:00'
    ELSE fnr.expires
  END AS expires,
  CASE
    WHEN NOW() > fnr.expires AND fnr.pool_name != 'Gnosis' THEN TRUE
    ELSE FALSE
  END AS service_fee
FROM filtered_named_results fnr;