"""
All the tools necessary to compose and encode a
Safe Multisend transaction consisting of Transfers
"""
import logging.config

from gnosis.eth.ethereum_client import EthereumClient
from gnosis.safe.multi_send import MultiSend, MultiSendTx

log = logging.getLogger(__name__)
logging.config.fileConfig(fname="logging.conf", disable_existing_loggers=False)

# This contract address can be removed once this issue is resolved:
# https://github.com/safe-global/safe-eth-py/issues/283
MULTISEND_CONTRACT = "0x40A2aCCbd92BCA938b02010E17A5b8929b49130D"


def build_encoded_multisend(
    transactions: list[MultiSendTx], client: EthereumClient
) -> bytes:
    """ "Encodes a list of transfers into Multisend Transaction"""
    # TODO - This doesn't appear to require a real Ethereum Client instance...
    multisend = MultiSend(address=MULTISEND_CONTRACT, ethereum_client=client)
    log.info(f"Packing {len(transactions)} transfers into MultiSend")
    tx_bytes: bytes = multisend.build_tx_data(transactions)
    return tx_bytes
