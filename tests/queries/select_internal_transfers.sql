select block_time,
       CONCAT('0x', ENCODE(tx_hash, 'hex')) as tx_hash,
       solver_address,
       solver_name,
       CONCAT('0x', ENCODE(token, 'hex'))   as token,
       amount,
       transfer_type
from incoming_and_outgoing_with_buffer_trades