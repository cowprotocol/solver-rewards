-- Partially structured stash of transaction
-- receipts containing settlement events.
-- Records will live here indefinitely and processed
-- as blocks finalize.
-- Note that this table is not guaranteed to contain
-- a complete history and may be periodically pruned to save space.
CREATE TABLE tx_receipts
(
    hash         bytea  NOT NULL,
    -- block at which transaction occurred
    block_number bigint NOT NULL,
    -- boolean field indicating whether transaction has been further processed.
    -- processing only occurs after current_block > block_number + 65
    processed    bool   NOT NULL DEFAULT false,
    -- any relevant content from transaction receipt.
    data         jsonb  NOT NULL
);

CREATE INDEX tx_receipt_idx ON tx_receipts (processed);
CREATE INDEX tx_receipt_idx_1 ON tx_receipts (block_number);