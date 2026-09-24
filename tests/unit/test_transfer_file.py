"""Tests for src/fetch/transfer_file.py's pre-proposal payout verification."""

import unittest
from unittest.mock import MagicMock, patch

from dune_client.types import Address

from src.fetch.transfer_file import (
    _to_verification_transfer,
    verify_payout_before_proposing,
)
from src.models.token import Token
from src.models.transfer import Transfer
from src.verification.compare_output_files import DuneReward

_COW = "0xdef1ca1fb7fbcdc777520aa7f396b4e015f497ab"
_RECEIVER = "0x" + "aa" * 20


class TestToVerificationTransfer(unittest.TestCase):
    def test_native_transfer(self):
        transfer = Transfer(
            token=None, recipient=Address(_RECEIVER), amount_wei=5 * 10**17
        )
        result = _to_verification_transfer(transfer)
        self.assertEqual(result.token_type, "native")
        self.assertEqual(result.token_address, "")
        self.assertEqual(result.receiver, _RECEIVER.lower())
        self.assertAlmostEqual(result.amount, 0.5)

    def test_erc20_transfer(self):
        token = Token(_COW, decimals=18)
        transfer = Transfer(
            token=token, recipient=Address(_RECEIVER), amount_wei=10 * 10**18
        )
        result = _to_verification_transfer(transfer)
        self.assertEqual(result.token_type, "erc20")
        self.assertEqual(result.token_address, _COW)
        self.assertAlmostEqual(result.amount, 10.0)


def _make_config() -> MagicMock:
    config = MagicMock()
    config.protocol_fee_config.protocol_fee_safe = Address(
        "0x22af3D38E50ddedeb7C47f36faB321eC3Bb72A76"
    )
    return config


class TestVerifyPayoutBeforeProposing(unittest.TestCase):
    def test_invalid_payout_returns_false(self):
        """A Dune reward with no corresponding transfer must fail verification."""
        rewards = [
            DuneReward(
                name="prod-A",
                solver_address="0x" + "bb" * 20,
                reward_target=_RECEIVER,
                quote_reward=10.0,
                native_token_transfer=0.0,
                cow_transfer=0.0,
            )
        ]
        with patch("src.fetch.transfer_file.fetch_dune_rewards", return_value=rewards):
            result = verify_payout_before_proposing([], [], MagicMock(), _make_config())
        self.assertFalse(result)

    def test_valid_payout_returns_true(self):
        """A matching transfer for every Dune reward must pass verification."""
        rewards = [
            DuneReward(
                name="prod-A",
                solver_address="0x" + "bb" * 20,
                reward_target=_RECEIVER,
                quote_reward=10.0,
                native_token_transfer=0.0,
                cow_transfer=0.0,
            )
        ]
        cow_transfer = Transfer(
            token=Token(_COW, decimals=18),
            recipient=Address(_RECEIVER),
            amount_wei=10 * 10**18,
        )
        with patch("src.fetch.transfer_file.fetch_dune_rewards", return_value=rewards):
            result = verify_payout_before_proposing(
                [cow_transfer], [], MagicMock(), _make_config()
            )
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
