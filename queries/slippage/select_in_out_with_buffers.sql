select block_time,
       tx_hash,
       solver_address,
       solver_name,
       CONCAT('0x', ENCODE(token_from, 'hex')) as token,
       amount_from as amount,
       transfer_type
from incoming_and_outgoing_with_buffer_trades
