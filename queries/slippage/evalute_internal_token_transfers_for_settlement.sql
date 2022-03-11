Select
    block_time,
    tx_hash,
    solver_address,
    solver_name,
    symbol,
    CONCAT('0x', ENCODE(token_from, 'hex')) as token_from,
    Case
        when token_to is null then token_to :: text
        else CONCAT('0x', ENCODE(token_to, 'hex'))
    end as token_to,
    amount_from,
    amount_to,
    transfer_type
from
    incoming_and_outcoming_with_buffer_trades