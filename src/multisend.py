"""
All the tools necessary to compose and encode a
Safe Multisend transaction consisting of Transfers
"""

from eth_typing.evm import ChecksumAddress
from safe_eth.eth.ethereum_client import EthereumClient
from safe_eth.eth.ethereum_network import EthereumNetwork
from safe_eth.safe.api import TransactionServiceApi
from safe_eth.safe.multi_send import MultiSend, MultiSendOperation, MultiSendTx
from safe_eth.safe.safe import Safe


from src.config import web3
from src.abis.load import weth9
from src.logger import set_log

log = set_log(__name__)

# This contract address can be removed once this issue is resolved:
# https://github.com/safe-global/safe-eth-py/issues/283
MULTISEND_CONTRACT = web3.to_checksum_address(
    "0x40A2aCCbd92BCA938b02010E17A5b8929b49130D"
)


def build_encoded_multisend(
    transactions: list[MultiSendTx], client: EthereumClient
) -> bytes:
    """ "Encodes a list of transfers into Multisend Transaction"""
    # TODO - This doesn't appear to require a real Ethereum Client instance...
    multisend = MultiSend(address=MULTISEND_CONTRACT, ethereum_client=client)
    log.info(f"Packing {len(transactions)} transfers into MultiSend")
    tx_bytes: bytes = multisend.build_tx_data(transactions)
    return tx_bytes


def prepend_unwrap_if_necessary(
    client: EthereumClient,
    safe_address: ChecksumAddress,
    transactions: list[MultiSendTx],
    wrapped_native_token: ChecksumAddress,
    skip_validation: bool = False,
) -> list[MultiSendTx]:
    """
    Given a list of multisend transactions, this checks that
    the total outgoing ETH is sufficient and unwraps entire WETH balance when it isn't.
    Raises if the ETH + WETH balance is still insufficient.
    """
    eth_balance = client.get_balance(web3.to_checksum_address(safe_address))
    # Amount of outgoing ETH from transfer
    eth_needed = sum(t.value for t in transactions)
    if eth_balance < eth_needed:
        weth = weth9(client.w3, wrapped_native_token)
        weth_balance = weth.functions.balanceOf(safe_address).call()
        if weth_balance + eth_balance < eth_needed:
            message = (
                f"{safe_address} has insufficient WETH + ETH balance for transaction!"
            )
            if not skip_validation:
                raise ValueError(message)
            log.warning(f"{message} - proceeding to build transaction anyway")

        log.info(f"prepending unwrap of {weth_balance/10**18}")
        transactions.insert(
            0,
            MultiSendTx(
                operation=MultiSendOperation.CALL,
                to=weth.address,
                value=0,
                data=weth.encodeABI(fn_name="withdraw", args=[weth_balance]),
            ),
        )
    return transactions


def post_multisend(
    safe_address: ChecksumAddress,
    network: EthereumNetwork,
    transactions: list[MultiSendTx],
    client: EthereumClient,
    signing_key: str,
    nonce_modifier: int = 0,
) -> int:
    """Posts a MultiSend Transaction from a list of Transfers."""
    # pylint: disable=too-many-arguments,too-many-positional-arguments

    encoded_multisend = build_encoded_multisend(transactions, client=client)
    safe = Safe(  # type: ignore  # pylint: disable=abstract-class-instantiated
        address=safe_address, ethereum_client=client
    )
    safe_tx = safe.build_multisig_tx(
        to=MULTISEND_CONTRACT,
        value=0,
        data=encoded_multisend,
        operation=MultiSendOperation.DELEGATE_CALL.value,
        safe_nonce=safe.retrieve_nonce() + nonce_modifier,
    )
    # There is a deep warning being raised here:
    # Details in issue: https://github.com/safe-global/safe-eth-py/issues/294
    safe_tx.sign(signing_key)
    tx_service = TransactionServiceApi(network, client)
    print(
        f"Posting transaction with hash"
        f" {safe_tx.safe_tx_hash.hex()} to {safe.address}"
    )
    tx_service.post_transaction(safe_tx=safe_tx)
    return int(safe_tx.safe_nonce)
