"""Decode Safe multisend calldata (copied from the Safe UI) into transfer/overdraft data.

The solver-payout proposal posts three separate multisend transactions to the Safe
(see ``src.fetch.transfer_file.auto_propose``): a COW-transfer multisend on the mainnet
Safe, a native-token-transfer multisend on the network Safe, and an overdrafts multisend
on the network Safe. Rather than requiring a Safe UI "Transaction export" CSV (which does
not exist for the overdrafts call at all, since it isn't a token transfer), this module
lets the operator paste the raw calldata for each of those three transactions - either as
a bare hex string, or as the JSON transaction object the Safe UI exposes - and decodes it
directly using the same contract ABIs used to build the transactions in the first place.

Note: compare_output_files.py only imports this module lazily, inside functions, so this
never actually cycles at runtime; the module-level import back into it below is still
flagged statically.
"""

# pylint: disable=cyclic-import

from __future__ import annotations

import csv
import json
from dataclasses import dataclass

from safe_eth.safe.multi_send import MultiSend

from src.abis.load import erc20, overdraftsmanager
from src.verification.compare_output_files import Transfer

_ERC20 = erc20()
_OVERDRAFTS = overdraftsmanager()


@dataclass(frozen=True)
class OverdraftEntry:
    """A single decoded `addOverdraft(account, amount)` call."""

    account: str
    wei: int

    @property
    def amount(self) -> float:
        """Overdraft amount in native token units."""
        return self.wei / 10**18


def extract_calldata(raw: str) -> str:
    """Returns the multisend calldata hex string from pasted user input.

    Accepts either a bare "0x..." calldata string, or the full Safe transaction
    JSON object (as copied from the Safe UI / tx-service), from which the "data"
    field is extracted.
    """
    raw = raw.strip()
    if not raw:
        raise ValueError("No calldata provided")
    if raw.startswith("0x") or raw.startswith("0X"):
        return raw
    payload = json.loads(raw)
    data = payload["data"]
    if not isinstance(data, str):
        raise ValueError("Pasted JSON has no string 'data' field")
    return data


def decode_transfers(
    raw: str, token_type: str, cow_token_address: str
) -> list[Transfer]:
    """Decodes a pasted COW-transfer or native-transfer multisend into a list of Transfer.

    token_type must be "erc20" (mainnet COW-transfer multisend) or "native"
    (network native-transfer multisend). A prepended WETH-unwrap call (present when
    the Safe's native balance needed topping up) is silently skipped, as it is not
    itself a payout.
    """
    if token_type not in ("erc20", "native"):
        raise ValueError(f"Unsupported token_type {token_type!r}")

    transfers = []
    for tx in MultiSend.from_transaction_data(extract_calldata(raw)):
        if token_type == "native":
            if len(tx.data) == 0 and tx.value > 0:
                transfers.append(
                    Transfer(
                        token_type="native",
                        token_address="",
                        receiver=tx.to.lower(),
                        amount=tx.value / 10**18,
                    )
                )
            # else: an internal call (e.g. WETH withdraw) - not a payout, skip it.
        else:
            try:
                _, params = _ERC20.decode_function_input(tx.data)
            except ValueError:
                continue
            transfers.append(
                Transfer(
                    token_type="erc20",
                    token_address=cow_token_address,
                    receiver=params["recipient"].lower(),
                    amount=params["amount"] / 10**18,
                )
            )
    return transfers


def decode_overdrafts(raw: str) -> list[OverdraftEntry]:
    """Decodes a pasted overdrafts multisend into a list of OverdraftEntry."""
    entries = []
    for tx in MultiSend.from_transaction_data(extract_calldata(raw)):
        try:
            _, params = _OVERDRAFTS.decode_function_input(tx.data)
        except ValueError:
            continue
        entries.append(
            OverdraftEntry(account=params["solver"].lower(), wei=params["amount"])
        )
    return entries


def write_transfers_csv(transfers: list[Transfer], path: str) -> None:
    """Writes a list of Transfer to a combined transfers CSV (as read by load_transfers)."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["token_type", "token_address", "receiver", "amount"]
        )
        writer.writeheader()
        for t in transfers:
            writer.writerow(
                {
                    "token_type": t.token_type,
                    "token_address": t.token_address,
                    "receiver": t.receiver,
                    "amount": t.amount,
                }
            )


def write_overdrafts_csv(entries: list[OverdraftEntry], path: str) -> None:
    """Writes a list of OverdraftEntry to a CSV file."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["account", "wei", "amount"])
        writer.writeheader()
        for e in entries:
            writer.writerow({"account": e.account, "wei": e.wei, "amount": e.amount})
