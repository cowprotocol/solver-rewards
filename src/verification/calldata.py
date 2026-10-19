"""Strict decoding of the MultiSend calldata of solver payout Safe transactions.

A payout MultiSend is ``multiSend(bytes)`` calldata, which the Safe
DELEGATECALLs MultiSendCallOnly with (see ``post_multisend`` in
``src/multisend.py``). Its packed inner transactions are classified into the
call types the payout script produces: a native transfer, an ERC-20
``transfer(address,uint256)`` or a wrapped native token ``withdraw(uint256)``
(see ``Transfer.as_multisend_tx`` and ``prepend_unwrap_if_necessary``).

The decoder does not use safe-eth-py or web3 to decode. The payouts are
encoded with safe-eth-py (``MultiSend.build_tx_data``), so a decoder built on
the same code would share its mistakes; safe-eth-py's
``MultiSend.from_transaction_data`` also returns an empty list for input it
cannot decode and ignores trailing bytes.

Anything the payout script would not have produced raises ``CalldataError``,
it is never skipped:

- function selectors other than the ones above, including known but
  unsupported ones such as the OverdraftsManager's ``addOverdraft``;
- inner operations other than CALL;
- native value attached to a contract call, and zero-amount calls;
- non-zero padding around ABI encoded addresses;
- non-canonical ABI offsets, non-zero ABI padding, truncated payloads and
  trailing bytes. MultiSendCallOnly skips up to 31 trailing bytes and parses
  32 or more as a further entry, so only payloads that consist exactly of
  complete entries decode to what the contract executes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Union

from eth_typing.evm import ChecksumAddress
from eth_utils.address import is_checksum_address, to_checksum_address

MULTI_SEND_SELECTOR = bytes.fromhex("8d80ff0a")
ERC20_TRANSFER_SELECTOR = bytes.fromhex("a9059cbb")
WITHDRAW_SELECTOR = bytes.fromhex("2e1a7d4d")

# Selectors that appear in payout Safe transactions but are not verified here.
UNSUPPORTED_SELECTORS = {
    bytes.fromhex("eb8e571d"): "addOverdraft(address,uint256)",
}

CALL = 0
DELEGATE_CALL = 1

UINT256_MAX = 2**256 - 1
WORD = 32

# operation (1 byte) + to (20 bytes) + value (32 bytes) + data length (32 bytes)
_PACKED_HEADER = 85
_ADDRESS_PATTERN = re.compile(r"0x[0-9a-fA-F]{40}")
_DECIMAL_PATTERN = re.compile(r"0|[1-9][0-9]*")


class CalldataError(ValueError):
    """Calldata is not exactly what the payout script produces."""


@dataclass(frozen=True)
class NativeTransfer:
    """Native token sent with a CALL that carries no calldata."""

    recipient: ChecksumAddress
    amount: int

    def __str__(self) -> str:
        return f"native transfer of {self.amount} wei to {self.recipient}"


@dataclass(frozen=True)
class Erc20Transfer:
    """ERC-20 ``transfer(recipient, amount)`` called on ``token``."""

    token: ChecksumAddress
    recipient: ChecksumAddress
    amount: int

    def __str__(self) -> str:
        return (
            f"ERC-20 transfer of {self.amount} atoms of {self.token} "
            f"to {self.recipient}"
        )


@dataclass(frozen=True)
class WrappedNativeWithdrawal:
    """``withdraw(amount)`` called on the wrapped native token ``token``."""

    token: ChecksumAddress
    amount: int

    def __str__(self) -> str:
        return f"withdrawal of {self.amount} wei from wrapped native token {self.token}"


PayoutCall = Union[NativeTransfer, Erc20Transfer, WrappedNativeWithdrawal]


@dataclass(frozen=True)
class InnerTransaction:
    """One packed MultiSend entry, before classification."""

    operation: int
    to: ChecksumAddress
    value: int
    data: bytes


def parse_address(value: object, what: str) -> ChecksumAddress:
    """Parse a 0x-prefixed address that is all lowercase or EIP-55 checksummed.

    Any other mixed-case spelling fails the EIP-55 checksum and is rejected.
    """
    if not isinstance(value, str) or not _ADDRESS_PATTERN.fullmatch(value):
        raise ValueError(
            f"{what}: expected a 0x-prefixed 20-byte address, got {value!r}"
        )
    if value[2:] != value[2:].lower() and not is_checksum_address(value):
        raise ValueError(f"{what}: {value} does not match its EIP-55 checksum")
    return to_checksum_address(value)


def parse_uint(value: object, what: str) -> int:
    """Parse an unsigned 256-bit integer given as a JSON integer or decimal string.

    Strings must be canonical ASCII decimals: no sign, whitespace, underscores,
    leading zeros or non-ASCII digits, all of which ``int()`` would accept.
    """
    if isinstance(value, bool):
        raise ValueError(f"{what}: expected an integer, got {value!r}")
    if isinstance(value, str) and _DECIMAL_PATTERN.fullmatch(value):
        number = int(value)
    elif isinstance(value, int):
        number = value
    else:
        raise ValueError(f"{what}: expected an integer, got {value!r}")
    if not 0 <= number <= UINT256_MAX:
        raise ValueError(f"{what}: {number} is not a uint256")
    return number


def abi_word(data: bytes, offset: int, what: str) -> bytes:
    """The 32-byte ABI word at ``offset``."""
    if offset + WORD > len(data):
        raise CalldataError(f"{what}: truncated, needs 32 bytes at offset {offset}")
    return data[offset : offset + WORD]


def abi_uint(word: bytes) -> int:
    """An ABI word as an unsigned integer."""
    return int.from_bytes(word, "big")


def abi_address(word: bytes, what: str) -> ChecksumAddress:
    """An ABI encoded address, whose 12 padding bytes must be zero."""
    if any(word[:12]):
        raise CalldataError(f"{what}: dirty address padding 0x{word[:12].hex()}")
    return to_checksum_address(word[12:])


def abi_bytes(args: bytes, offset: int, what: str) -> tuple[bytes, int]:
    """The ABI ``bytes`` value whose length word is at ``offset``.

    Returns the value and the offset just after its padding, which must be zero.
    """
    length = abi_uint(abi_word(args, offset, f"{what} length"))
    start = offset + WORD
    if length > len(args) - start:
        raise CalldataError(
            f"{what}: declares {length} bytes but only {len(args) - start} follow"
        )
    end = start + (length + WORD - 1) // WORD * WORD
    if end > len(args):
        raise CalldataError(f"{what}: truncated padding")
    if any(args[start + length : end]):
        raise CalldataError(f"{what}: non-zero padding")
    return args[start : start + length], end


def decode_multisend(data: bytes) -> list[InnerTransaction]:
    """Split canonical ``multiSend(bytes)`` calldata into its packed entries."""
    if data[:4] != MULTI_SEND_SELECTOR:
        raise CalldataError(f"not a multiSend call: selector 0x{data[:4].hex()}")
    args = data[4:]
    offset = abi_uint(abi_word(args, 0, "multiSend offset"))
    if offset != WORD:
        raise CalldataError(f"multiSend: non-canonical offset {offset}")
    payload, end = abi_bytes(args, WORD, "multiSend transactions")
    if end != len(args):
        raise CalldataError(f"multiSend: {len(args) - end} trailing bytes")
    if not payload:
        raise CalldataError("multiSend: no transactions")

    transactions: list[InnerTransaction] = []
    position = 0
    while position < len(payload):
        index = len(transactions)
        data_start = position + _PACKED_HEADER
        if data_start > len(payload):
            raise CalldataError(
                f"inner transaction {index}: truncated header, "
                f"{len(payload) - position} of {_PACKED_HEADER} bytes"
            )
        length = abi_uint(payload[position + 53 : data_start])
        if length > len(payload) - data_start:
            raise CalldataError(
                f"inner transaction {index}: declares {length} data bytes "
                f"but only {len(payload) - data_start} remain"
            )
        transactions.append(
            InnerTransaction(
                operation=payload[position],
                to=to_checksum_address(payload[position + 1 : position + 21]),
                value=abi_uint(payload[position + 21 : position + 53]),
                data=payload[data_start : data_start + length],
            )
        )
        position = data_start + length
    return transactions


def classify(index: int, transaction: InnerTransaction) -> PayoutCall:
    """Classify an inner transaction as one of the payout call types."""
    where = f"inner transaction {index}"
    if transaction.operation != CALL:
        raise CalldataError(
            f"{where}: operation {transaction.operation} is not CALL ({CALL})"
        )
    data = transaction.data
    if not data:
        if transaction.value == 0:
            raise CalldataError(f"{where}: zero-value call without calldata")
        return NativeTransfer(recipient=transaction.to, amount=transaction.value)
    if len(data) < 4:
        raise CalldataError(f"{where}: {len(data)} bytes of calldata, no selector")
    selector = data[:4]
    if selector == ERC20_TRANSFER_SELECTOR:
        _check_contract_call(where, transaction, "transfer(address,uint256)", 68)
        call: PayoutCall = Erc20Transfer(
            token=transaction.to,
            recipient=abi_address(data[4:36], f"{where} recipient"),
            amount=abi_uint(data[36:68]),
        )
    elif selector == WITHDRAW_SELECTOR:
        _check_contract_call(where, transaction, "withdraw(uint256)", 36)
        call = WrappedNativeWithdrawal(token=transaction.to, amount=abi_uint(data[4:]))
    else:
        name = UNSUPPORTED_SELECTORS.get(selector)
        raise CalldataError(
            f"{where}: unsupported function selector 0x{selector.hex()}"
            + (f" ({name}), this transaction type is not verified" if name else "")
        )
    if call.amount == 0:
        raise CalldataError(f"{where}: zero amount in {call}")
    return call


def _check_contract_call(
    where: str, transaction: InnerTransaction, signature: str, size: int
) -> None:
    if len(transaction.data) != size:
        raise CalldataError(
            f"{where}: {signature} calldata must be {size} bytes, "
            f"got {len(transaction.data)}"
        )
    if transaction.value != 0:
        raise CalldataError(
            f"{where}: {signature} call carries native value {transaction.value}"
        )


def decode_payout_calls(data: bytes) -> list[PayoutCall]:
    """Decode ``multiSend(bytes)`` calldata into typed payout calls, in order."""
    return [
        classify(index, transaction)
        for index, transaction in enumerate(decode_multisend(data))
    ]
