"""Expected inner calls of a payout MultiSend, derived from the payout's transfers.

The calls are derived from the payout intent, the ``Transfer`` objects the
payout script is given, and never from a transaction or its encoding: nothing
here calls ``Transfer.as_multisend_tx`` or uses ``src.multisend``, safe-eth-py
or web3. ``Transfer`` is imported for type checking only, because importing
``src.models.transfer`` loads safe-eth-py.

Each transfer is paid with one call, as ``Transfer.as_multisend_tx`` encodes
it:

- ``token is None``: a native transfer of ``amount_wei`` to the recipient;
- any other transfer, the wrapped native token included: an ERC-20
  ``transfer`` of ``amount_wei`` to the recipient, called on the token.

``Transfer`` and ``Token`` addresses are ``dune_client`` ``Address`` objects,
which store lowercase hex. The calls hold EIP-55 checksums, as the decoder
returns them.

``main`` in ``src/fetch/transfer_file.py`` pays transfers of the wrapped native
token in the native token transaction, which ``auto_propose`` passes through
``prepend_unwrap_if_necessary`` (``src/multisend.py``). Its rule is restated
here: if the Safe's native balance is less than the sum of the native
transfers, the first call withdraws exactly the difference from the wrapped
native token. ERC-20 transfers carry no native value, so transfers of the
wrapped native token do not count towards that sum. The COW transaction never
unwraps: ``auto_propose`` passes ``wrapped_amount=None`` for it.

Inputs the payout script cannot build a transaction from raise
``ValueError``: an amount or balance that is not a uint256, a transfer of
zero, an invalid wrapped native token address and an unwrap larger than a
uint256.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from eth_typing.evm import ChecksumAddress
from eth_utils.address import to_checksum_address

from src.verification.calldata import (
    UINT256_MAX,
    Erc20Transfer,
    NativeTransfer,
    PayoutCall,
    WrappedNativeWithdrawal,
    parse_address,
    parse_uint,
)

if TYPE_CHECKING:
    from src.models.transfer import Transfer


def transfer_calls(transfers: Sequence[Transfer]) -> tuple[PayoutCall, ...]:
    """The call that pays each transfer, in the order of the transfers."""
    return tuple(
        _transfer_call(transfer, f"transfers[{index}]")
        for index, transfer in enumerate(transfers)
    )


def expected_unwrap(
    transfers: Sequence[Transfer],
    *,
    native_balance: int,
    wrapped_native_token: ChecksumAddress,
) -> WrappedNativeWithdrawal | None:
    """The unwrap a native token transaction paying ``transfers`` starts with.

    ``native_balance`` is the Safe's native token balance as read in the same
    payout run. Returns ``None`` if the balance covers the native transfers.
    """
    return _unwrap(transfer_calls(transfers), native_balance, wrapped_native_token)


def cow_multisend_calls(transfers: Sequence[Transfer]) -> tuple[PayoutCall, ...]:
    """The calls of the COW transaction: the transfer calls, never an unwrap."""
    return transfer_calls(transfers)


def native_multisend_calls(
    transfers: Sequence[Transfer],
    *,
    native_balance: int,
    wrapped_native_token: ChecksumAddress,
) -> tuple[PayoutCall, ...]:
    """The calls of the native token transaction: the unwrap, if any, first."""
    calls = transfer_calls(transfers)
    unwrap = _unwrap(calls, native_balance, wrapped_native_token)
    return calls if unwrap is None else (unwrap, *calls)


def _transfer_call(transfer: Transfer, what: str) -> PayoutCall:
    amount = parse_uint(transfer.amount_wei, f"{what}.amount_wei")
    if amount == 0:
        raise ValueError(f"{what}.amount_wei: must be greater than zero")
    recipient = to_checksum_address(transfer.recipient.address)
    if transfer.token is None:
        return NativeTransfer(recipient=recipient, amount=amount)
    return Erc20Transfer(
        token=to_checksum_address(transfer.token.address.address),
        recipient=recipient,
        amount=amount,
    )


def _unwrap(
    calls: Sequence[PayoutCall],
    native_balance: int,
    wrapped_native_token: ChecksumAddress,
) -> WrappedNativeWithdrawal | None:
    token = parse_address(wrapped_native_token, "wrapped_native_token")
    balance = parse_uint(native_balance, "native_balance")
    native_value = sum(
        call.amount for call in calls if isinstance(call, NativeTransfer)
    )
    shortfall = native_value - balance
    if shortfall <= 0:
        return None
    if shortfall > UINT256_MAX:
        raise ValueError(f"unwrap: {shortfall} wei is not a uint256")
    return WrappedNativeWithdrawal(token=token, amount=shortfall)
