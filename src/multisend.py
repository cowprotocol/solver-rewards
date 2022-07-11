"""
All the tools necessary to compose and encode a
Safe Multisend transaction consisting of Transfers
"""
import logging.config

from eth_typing.evm import ChecksumAddress
from gnosis.eth.ethereum_client import EthereumClient
from gnosis.eth.ethereum_network import EthereumNetwork
from gnosis.safe.safe import Safe
from gnosis.safe.multi_send import MultiSend, MultiSendOperation, MultiSendTx

# This dependency can be removed once this issue is resolved:
# https://github.com/safe-global/safe-eth-py/issues/284
from safe_cli.api.transaction_service_api import TransactionServiceApi

from src.constants import ETH_CLIENT

log = logging.getLogger(__name__)
logging.config.fileConfig(fname="logging.conf", disable_existing_loggers=False)

# This contract address can be removed once this issue is resolved:
# https://github.com/safe-global/safe-eth-py/issues/283
MULTISEND_CONTRACT = "0x40A2aCCbd92BCA938b02010E17A5b8929b49130D"


def build_encoded_multisend(
    transactions: list[MultiSendTx], client: EthereumClient = ETH_CLIENT
) -> bytes:
    """ "Encodes a list of transfers into Multisend Transaction"""
    # TODO - This doesn't appear to require a real Ethereum Client instance...
    multisend = MultiSend(address=MULTISEND_CONTRACT, ethereum_client=client)
    log.info(f"Packing {len(transactions)} transfers into MultiSend")
    tx_bytes: bytes = multisend.build_tx_data(transactions)
    return tx_bytes


def post_multisend(
    safe_address: ChecksumAddress,
    network: EthereumNetwork,
    transfers: list[MultiSendTx],
    client: EthereumClient,
    signing_key: str,
) -> None:
    """Posts a MultiSend Transaction from a list of Transfers."""
    encoded_multisend = build_encoded_multisend(transactions=transfers)
    safe = Safe(address=safe_address, ethereum_client=client)
    safe_tx = safe.build_multisig_tx(
        to=MULTISEND_CONTRACT,
        value=0,
        data=encoded_multisend,
        operation=MultiSendOperation.DELEGATE_CALL.value,
    )
    # There is a deep warning being raised here:
    # Details in issue: https://github.com/safe-global/safe-eth-py/issues/294
    safe_tx.sign(signing_key)
    tx_service = TransactionServiceApi(ETH_CLIENT, network)
    # TODO - simulate transaction and fail if simulation fails.
    print(
        f"Posting transaction with hash"
        f" {safe_tx.safe_tx_hash.hex()} to {safe.address}"
    )
    tx_service.post_transaction(safe_address=safe.address, safe_tx=safe_tx)
