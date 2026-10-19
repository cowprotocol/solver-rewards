"""Safe transactions and independent recomputation of their safeTxHash.

``SafeTransaction`` holds exactly the values a Safe owner signs: the EIP-712
``SafeTx`` struct, the Safe it is addressed to and the chain it is for. It can
be read from a Safe Transaction Service record or from executed
``execTransaction`` calldata.

The hash is recomputed from the definitions in the Safe contracts, without
safe-eth-py. ``GnosisSafe.sol`` v1.3.0 and ``Safe.sol`` v1.4.1 use the same
type hashes and encoding:

    domainSeparator = keccak256(abi.encode(DOMAIN_SEPARATOR_TYPEHASH, chainId, safe))
    safeTxHash = keccak256(0x19 || 0x01 || domainSeparator || keccak256(abi.encode(
        SAFE_TX_TYPEHASH, to, value, keccak256(data), operation, safeTxGas,
        baseGas, gasPrice, gasToken, refundReceiver, nonce)))

This covers Safes from v1.3.0 on, which includes every payout Safe (v1.3.0,
v1.3.0+L2 and v1.4.1). Older Safes leave chainId out of the domain; their
recomputed hash does not match, so verifying them fails.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from eth_typing.evm import ChecksumAddress
from eth_utils.address import is_checksum_address
from eth_utils.crypto import keccak

from src.verification.calldata import (
    CALL,
    DELEGATE_CALL,
    UINT256_MAX,
    WORD,
    CalldataError,
    abi_address,
    abi_bytes,
    abi_uint,
    abi_word,
    parse_address,
    parse_uint,
)

EXEC_TRANSACTION_SELECTOR = bytes.fromhex("6a761202")

# keccak256("EIP712Domain(uint256 chainId,address verifyingContract)")
DOMAIN_SEPARATOR_TYPEHASH = bytes.fromhex(
    "47e79534a245952e8b16893a336b85a3d9ea9fa8c573f3d803afb92a79469218"
)
# keccak256("SafeTx(address to,uint256 value,bytes data,uint8 operation,
#   uint256 safeTxGas,uint256 baseGas,uint256 gasPrice,address gasToken,
#   address refundReceiver,uint256 nonce)")
SAFE_TX_TYPEHASH = bytes.fromhex(
    "bb8310d486368db6bd6f849402fdd73ad53d316b5a4b2644ad6efe0f941286d8"
)

_EXEC_TRANSACTION_HEAD = 10 * WORD
_HEX_DATA_PATTERN = re.compile(r"0x(?:[0-9a-fA-F]{2})*")
_HASH_PATTERN = re.compile(r"0x[0-9a-fA-F]{64}")
_SERVICE_FIELDS = (
    "safe",
    "to",
    "value",
    "data",
    "operation",
    "safeTxGas",
    "baseGas",
    "gasPrice",
    "gasToken",
    "refundReceiver",
    "nonce",
    "safeTxHash",
)


@dataclass(frozen=True)
class SafeTransaction:
    """The signed fields of a Safe transaction, bound to a Safe and a chain."""

    # pylint: disable=too-many-instance-attributes

    chain_id: int
    safe: ChecksumAddress
    to: ChecksumAddress
    value: int
    data: bytes
    operation: int
    safe_tx_gas: int
    base_gas: int
    gas_price: int
    gas_token: ChecksumAddress
    refund_receiver: ChecksumAddress
    nonce: int

    def __post_init__(self) -> None:
        for name in ("safe", "to", "gas_token", "refund_receiver"):
            if not is_checksum_address(getattr(self, name)):
                raise ValueError(f"{name}: {getattr(self, name)!r} is not checksummed")
        for name in ("value", "safe_tx_gas", "base_gas", "gas_price", "nonce"):
            if not 0 <= getattr(self, name) <= UINT256_MAX:
                raise ValueError(f"{name}: {getattr(self, name)} is not a uint256")
        if not 0 < self.chain_id <= UINT256_MAX:
            raise ValueError(f"chain_id: {self.chain_id} is not a valid chain id")
        if self.operation not in (CALL, DELEGATE_CALL):
            raise ValueError(f"operation: {self.operation} is not CALL or DELEGATECALL")

    @classmethod
    def from_transaction_service(
        cls, record: Mapping[str, Any], chain_id: int
    ) -> tuple[SafeTransaction, bytes]:
        """Parse a multisig transaction as returned by the Safe Transaction Service.

        ``chain_id`` is the chain of the service instance the record came from;
        records do not contain it. Returns the transaction and the safeTxHash
        the service reported for it.
        """
        missing = [name for name in _SERVICE_FIELDS if name not in record]
        if missing:
            raise ValueError(f"missing fields: {', '.join(missing)}")
        data = "0x" if record["data"] is None else record["data"]
        if not isinstance(data, str) or not _HEX_DATA_PATTERN.fullmatch(data):
            raise ValueError(f"data: expected 0x-prefixed hex bytes, got {data!r}")
        reported = record["safeTxHash"]
        if not isinstance(reported, str) or not _HASH_PATTERN.fullmatch(reported):
            raise ValueError(f"safeTxHash: expected a 32-byte hash, got {reported!r}")
        transaction = cls(
            chain_id=chain_id,
            safe=parse_address(record["safe"], "safe"),
            to=parse_address(record["to"], "to"),
            value=parse_uint(record["value"], "value"),
            data=bytes.fromhex(data[2:]),
            operation=parse_uint(record["operation"], "operation"),
            safe_tx_gas=parse_uint(record["safeTxGas"], "safeTxGas"),
            base_gas=parse_uint(record["baseGas"], "baseGas"),
            gas_price=parse_uint(record["gasPrice"], "gasPrice"),
            gas_token=parse_address(record["gasToken"], "gasToken"),
            refund_receiver=parse_address(record["refundReceiver"], "refundReceiver"),
            nonce=parse_uint(record["nonce"], "nonce"),
        )
        return transaction, bytes.fromhex(reported[2:])

    def domain_separator(self) -> bytes:
        """EIP-712 domain separator of the Safe on this chain."""
        return keccak(
            DOMAIN_SEPARATOR_TYPEHASH
            + _uint_word(self.chain_id)
            + _address_word(self.safe)
        )

    def safe_tx_hash(self) -> bytes:
        """The EIP-712 hash Safe owners sign for this transaction."""
        struct_hash = keccak(
            SAFE_TX_TYPEHASH
            + _address_word(self.to)
            + _uint_word(self.value)
            + keccak(self.data)
            + _uint_word(self.operation)
            + _uint_word(self.safe_tx_gas)
            + _uint_word(self.base_gas)
            + _uint_word(self.gas_price)
            + _address_word(self.gas_token)
            + _address_word(self.refund_receiver)
            + _uint_word(self.nonce)
        )
        return keccak(b"\x19\x01" + self.domain_separator() + struct_hash)


def decode_exec_transaction(
    calldata: bytes, *, chain_id: int, safe: str, nonce: int
) -> tuple[SafeTransaction, bytes]:
    """Decode canonical ``execTransaction`` calldata sent to ``safe``.

    The calldata does not contain the Safe (the recipient of the call), the
    chain or the nonce (the Safe's nonce when it executed), so they are passed
    in. The encoding must be exactly what a standard ABI encoder produces:
    offsets pointing right after the head and after the previous value, zero
    padding and no trailing bytes. Returns the transaction and the signatures.
    """
    if calldata[:4] != EXEC_TRANSACTION_SELECTOR:
        raise CalldataError(
            f"not an execTransaction call: selector 0x{calldata[:4].hex()}"
        )
    args = calldata[4:]
    head = [abi_word(args, i * WORD, f"execTransaction word {i}") for i in range(10)]
    if abi_uint(head[2]) != _EXEC_TRANSACTION_HEAD:
        raise CalldataError(
            f"execTransaction: non-canonical data offset {abi_uint(head[2])}"
        )
    operation = abi_uint(head[3])
    if operation not in (CALL, DELEGATE_CALL):
        raise CalldataError(f"execTransaction: invalid operation {operation}")
    data, data_end = abi_bytes(args, _EXEC_TRANSACTION_HEAD, "execTransaction data")
    if abi_uint(head[9]) != data_end:
        raise CalldataError(
            f"execTransaction: non-canonical signatures offset {abi_uint(head[9])}"
        )
    signatures, end = abi_bytes(args, data_end, "execTransaction signatures")
    if end != len(args):
        raise CalldataError(f"execTransaction: {len(args) - end} trailing bytes")
    transaction = SafeTransaction(
        chain_id=chain_id,
        safe=parse_address(safe, "safe"),
        to=abi_address(head[0], "execTransaction to"),
        value=abi_uint(head[1]),
        data=data,
        operation=operation,
        safe_tx_gas=abi_uint(head[4]),
        base_gas=abi_uint(head[5]),
        gas_price=abi_uint(head[6]),
        gas_token=abi_address(head[7], "execTransaction gasToken"),
        refund_receiver=abi_address(head[8], "execTransaction refundReceiver"),
        nonce=nonce,
    )
    return transaction, signatures


def _uint_word(value: int) -> bytes:
    return value.to_bytes(WORD, "big")


def _address_word(address: str) -> bytes:
    return bytes(12) + bytes.fromhex(address[2:])
