"""Tests for src/verification/compare_output_files.py."""
import os
import textwrap
import unittest

from src.verification.compare_output_files import (
    DEFAULT_COW_THRESHOLD,
    DEFAULT_NATIVE_THRESHOLD,
    DuneReward,
    FeeSummary,
    Transfer,
    load_fee_summary,
    load_safe_transfers,
    compare_safe_exports,
)

_COW = "0xdef1ca1fb7fbcdc777520aa7f396b4e015f497ab"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXAMPLES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "e2e", "2026-06-16-arbitrum"
)

_ARB_NATIVE_CSV = os.path.join(
    EXAMPLES_DIR,
    "transfers-arbitrum-2026-06-16 - transactions_export_42161_"
    "0x66331f0b9cb30d38779c786Bda5a3d57d12fbA50_1781886076501.csv.csv",
)
_MAINNET_COW_CSV = os.path.join(
    EXAMPLES_DIR,
    "transfers-mainnet-for-arbitrum-2026-06-16 - transactions_export_1_"
    "0xA03be496e67Ec29bC62F01a428683D7F9c204930_1781885784513.csv.csv",
)
_DUNE_CSV = os.path.join(EXAMPLES_DIR, "Period_Solver_Rewards.csv")


def _reward(
    name: str,
    solver: str,
    target: str,
    quote: float = 0.0,
    native: float = 0.0,
    cow: float = 0.0,
) -> DuneReward:
    return DuneReward(
        name=name,
        solver_address=solver.lower(),
        reward_target=target.lower(),
        quote_reward=quote,
        native_token_transfer=native,
        cow_transfer=cow,
    )


def _cow_t(receiver: str, amount: float) -> Transfer:
    return Transfer(
        token_type="erc20",
        token_address=_COW,
        receiver=receiver.lower(),
        amount=amount,
    )


def _native_t(receiver: str, amount: float) -> Transfer:
    return Transfer(
        token_type="native",
        token_address="",
        receiver=receiver.lower(),
        amount=amount,
    )


# ---------------------------------------------------------------------------
# load_safe_transfers
# ---------------------------------------------------------------------------


class TestLoadSafeTransfers(unittest.TestCase):
    def _write_csv(self, content: str) -> str:
        import tempfile

        path = tempfile.mktemp(suffix=".csv")
        with open(path, "w") as f:
            f.write(textwrap.dedent(content))
        return path

    def test_filters_incoming_rows(self):
        """Rows where From Address != Safe Address must be skipped."""
        path = self._write_csv(
            """\
            Nonce,Safe Address,From Address,To Address,Transaction Hash,Contract Address,Amount,Asset Type,Asset Symbol,Created at,Executed at,Proposer Address,Executor Address,Note,Amount Gas,Gas token
            1,0xSafe,0xWETH,0xSafe,,, 5.0,native,ETH,,,,,,0,
            1,0xSafe,0xSafe,0xReceiver,,,5.0,native,ETH,,,,,,0,
            """
        )
        transfers = load_safe_transfers(path, _COW)
        self.assertEqual(len(transfers), 1)
        self.assertEqual(transfers[0].receiver, "0xreceiver")

    def test_filters_zero_address(self):
        """Rows with To Address == 0x000…000 (WETH burn) must be skipped."""
        zero = "0x" + "0" * 40
        path = self._write_csv(
            f"""\
            Nonce,Safe Address,From Address,To Address,Transaction Hash,Contract Address,Amount,Asset Type,Asset Symbol,Created at,Executed at,Proposer Address,Executor Address,Note,Amount Gas,Gas token
            1,0xSafe,0xSafe,{zero},,,6.0,erc20,WETH,,,,,,0,
            1,0xSafe,0xSafe,0xReceiver,,,3.0,native,ETH,,,,,,0,
            """
        )
        transfers = load_safe_transfers(path, _COW)
        self.assertEqual(len(transfers), 1)
        self.assertEqual(transfers[0].token_type, "native")

    def test_erc20_assigned_cow_token(self):
        """ERC-20 rows get the passed cow_token_address as their token address."""
        path = self._write_csv(
            """\
            Nonce,Safe Address,From Address,To Address,Transaction Hash,Contract Address,Amount,Asset Type,Asset Symbol,Created at,Executed at,Proposer Address,Executor Address,Note,Amount Gas,Gas token
            1,0xSafe,0xSafe,0xSolver,,,100.0,erc20,COW,,,,,,0,
            """
        )
        transfers = load_safe_transfers(path, _COW)
        self.assertEqual(len(transfers), 1)
        self.assertEqual(transfers[0].token_type, "erc20")
        self.assertEqual(transfers[0].token_address, _COW)
        self.assertAlmostEqual(transfers[0].amount, 100.0)

    def test_skips_empty_rows(self):
        """Rows with empty To Address or Amount must be skipped."""
        path = self._write_csv(
            """\
            Nonce,Safe Address,From Address,To Address,Transaction Hash,Contract Address,Amount,Asset Type,Asset Symbol,Created at,Executed at,Proposer Address,Executor Address,Note,Amount Gas,Gas token
            ,,,,,,,,,,,,,,,
            1,0xSafe,0xSafe,0xSolver,,,50.0,erc20,COW,,,,,,0,
            """
        )
        transfers = load_safe_transfers(path, _COW)
        self.assertEqual(len(transfers), 1)

    def test_real_arbitrum_safe_csv(self):
        """Parses the 2026-06-16 Arbitrum native Safe export.

        Expected: 9 outgoing native transfers (WETH burn to zero address and
        the incoming WETH-unwrap row are both excluded).
        """
        if not os.path.exists(_ARB_NATIVE_CSV):
            self.skipTest("Arbitrum Safe CSV not present")
        transfers = load_safe_transfers(_ARB_NATIVE_CSV, _COW)
        native = [t for t in transfers if t.token_type == "native"]
        erc20 = [t for t in transfers if t.token_type == "erc20"]
        self.assertEqual(len(native), 9)
        self.assertEqual(len(erc20), 0)

    def test_real_mainnet_cow_safe_csv(self):
        """Parses the 2026-06-16 mainnet COW Safe export.

        Expected: 31 outgoing ERC-20 COW transfers (empty trailing rows are
        excluded).
        """
        if not os.path.exists(_MAINNET_COW_CSV):
            self.skipTest("Mainnet COW Safe CSV not present")
        transfers = load_safe_transfers(_MAINNET_COW_CSV, _COW)
        self.assertEqual(len(transfers), 31)
        for t in transfers:
            self.assertEqual(t.token_type, "erc20")
            self.assertEqual(t.token_address, _COW)


# ---------------------------------------------------------------------------
# compare_safe_exports — unit tests with synthetic data
# ---------------------------------------------------------------------------


class TestCompareSafeExports(unittest.TestCase):
    def test_all_transfers_present_no_errors(self):
        rewards = [
            _reward("prod-A", "0xAA", "0xTA", quote=10.0, native=0.5, cow=100.0),
        ]
        cow_transfers = [_cow_t("0xTA", 10.0), _cow_t("0xTA", 100.0)]
        native_transfers = [_native_t("0xTA", 0.5)]

        report = compare_safe_exports(rewards, cow_transfers, native_transfers, _COW)

        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])
        self.assertAlmostEqual(report.totals.quote, 10.0)
        self.assertAlmostEqual(report.totals.native, 0.5)
        self.assertAlmostEqual(report.totals.solve, 100.0)

    def test_missing_quote_cow_transfer_is_error(self):
        rewards = [_reward("prod-A", "0xAA", "0xTA", quote=10.0)]
        report = compare_safe_exports(rewards, [], [], _COW)
        self.assertEqual(len(report.errors), 1)
        self.assertIn("missing quote reward", report.errors[0].message)

    def test_missing_solve_cow_transfer_is_error(self):
        rewards = [_reward("prod-A", "0xAA", "0xTA", cow=50.0)]
        report = compare_safe_exports(rewards, [], [], _COW)
        self.assertEqual(len(report.errors), 1)
        self.assertIn("missing solve reward", report.errors[0].message)

    def test_missing_native_transfer_is_error(self):
        rewards = [_reward("prod-A", "0xAA", "0xTA", native=0.1)]
        report = compare_safe_exports(rewards, [], [], _COW)
        self.assertEqual(len(report.errors), 1)
        self.assertIn("missing native transfer", report.errors[0].message)

    def test_native_below_threshold_is_not_required(self):
        rewards = [_reward("prod-A", "0xAA", "0xTA", native=DEFAULT_NATIVE_THRESHOLD * 0.5)]
        report = compare_safe_exports(rewards, [], [], _COW)
        self.assertEqual(report.errors, [])

    def test_cow_below_threshold_is_not_required(self):
        rewards = [_reward("prod-A", "0xAA", "0xTA", cow=DEFAULT_COW_THRESHOLD * 0.5)]
        report = compare_safe_exports(rewards, [], [], _COW)
        self.assertEqual(report.errors, [])

    def test_unmatched_native_transfer_is_warning(self):
        """A native transfer with no matching Dune entry → unmatched warning."""
        rewards = [_reward("prod-A", "0xAA", "0xTA")]
        native_transfers = [_native_t("0xFEE", 1.5)]

        report = compare_safe_exports(rewards, [], native_transfers, _COW)

        self.assertEqual(report.errors, [])
        self.assertEqual(len(report.warnings), 1)
        self.assertIn("Unmatched transfer", report.warnings[0].message)
        self.assertEqual(report.unmatched_transfers, native_transfers)

    def test_wrong_token_address_is_error(self):
        wrong_token = "0x" + "ff" * 20
        rewards = [_reward("prod-A", "0xAA", "0xTA", cow=100.0)]
        cow_transfers = [
            Transfer(
                token_type="erc20",
                token_address=wrong_token,
                receiver="0xta",
                amount=100.0,
            )
        ]
        report = compare_safe_exports(rewards, cow_transfers, [], _COW)
        errors = [e.message for e in report.errors]
        self.assertTrue(any("uses token" in m for m in errors))

    def test_native_sent_to_solver_address_is_warning(self):
        solver = "0xsolveraddress"
        target = "0xrewardtarget"
        rewards = [_reward("prod-A", solver, target, native=0.1)]
        native_transfers = [_native_t(solver, 0.1)]

        report = compare_safe_exports(rewards, [], native_transfers, _COW)

        self.assertEqual(report.errors, [])
        self.assertEqual(len(report.warnings), 1)
        self.assertIn("solver address", report.warnings[0].message)

    def test_shared_reward_target_distinguishes_by_amount(self):
        """Two solvers share a reward_target; transfers are matched by amount."""
        shared = "0xshared"
        rewards = [
            _reward("prod-A", "0xaa", shared, quote=100.0, cow=500.0),
            _reward("prod-B", "0xbb", shared, quote=200.0, cow=300.0),
        ]
        cow_transfers = [
            _cow_t(shared, 100.0),
            _cow_t(shared, 500.0),
            _cow_t(shared, 200.0),
            _cow_t(shared, 300.0),
        ]
        report = compare_safe_exports(rewards, cow_transfers, [], _COW)
        self.assertEqual(report.errors, [])
        self.assertAlmostEqual(report.totals.quote, 300.0)
        self.assertAlmostEqual(report.totals.solve, 800.0)

    def test_amount_within_tolerance_matches(self):
        rewards = [_reward("prod-A", "0xAA", "0xTA", cow=100.0)]
        # 1 part-per-million deviation — well within 0.01 % tolerance.
        cow_transfers = [_cow_t("0xTA", 100.0001)]
        report = compare_safe_exports(rewards, cow_transfers, [], _COW)
        self.assertEqual(report.errors, [])

    def test_overdraft_solver_zero_transfers_is_ok(self):
        """A solver with no expected transfers produces no errors."""
        rewards = [_reward("prod-A", "0xAA", "0xTA", quote=0.0, native=0.0, cow=0.0)]
        report = compare_safe_exports(rewards, [], [], _COW)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])


# ---------------------------------------------------------------------------
# load_fee_summary
# ---------------------------------------------------------------------------


class TestLoadFeeSummary(unittest.TestCase):
    def _write_csv(self, content: str) -> str:
        import tempfile

        path = tempfile.mktemp(suffix=".csv")
        with open(path, "w") as f:
            f.write(textwrap.dedent(content))
        return path

    def test_parses_protocol_fee(self):
        path = self._write_csv(
            """\
            outgoing_native_token,protocol_fee_in_native_token,fees_native_token
            0,2.038193570744012,7.068761780931671
            """
        )
        summary = load_fee_summary(path)
        self.assertAlmostEqual(summary.protocol_fee, 2.038193570744012)

    def test_real_fees_csv(self):
        fees_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "e2e",
            "2026-06-16-arbitrum",
            "V3_Weekly_Cost_Coverage_Fees_-_Reimbursement.csv",
        )
        if not os.path.exists(fees_path):
            self.skipTest("Fees CSV not present")
        summary = load_fee_summary(fees_path)
        self.assertAlmostEqual(summary.protocol_fee, 2.038193570744012, places=6)


# ---------------------------------------------------------------------------
# compare_safe_exports — protocol fee verification
# ---------------------------------------------------------------------------


class TestCompareSafeExportsWithFees(unittest.TestCase):
    def test_protocol_fee_verified_and_removed_from_unmatched(self):
        protocol_safe = "0xdaosafe"
        rewards = [_reward("prod-A", "0xAA", "0xTA")]
        native_transfers = [
            _native_t(protocol_safe, 2.038),
            _native_t("0xpartner", 0.5),
        ]
        report = compare_safe_exports(
            rewards,
            [],
            native_transfers,
            _COW,
            protocol_fee=2.038,
            protocol_fee_safe=protocol_safe,
        )
        self.assertEqual(report.errors, [])
        # Only the partner transfer should remain unmatched.
        self.assertEqual(len(report.unmatched_transfers), 1)
        self.assertEqual(report.unmatched_transfers[0].receiver, "0xpartner")

    def test_missing_protocol_fee_is_error(self):
        protocol_safe = "0xdaosafe"
        rewards = [_reward("prod-A", "0xAA", "0xTA")]
        report = compare_safe_exports(
            rewards,
            [],
            [],
            _COW,
            protocol_fee=2.038,
            protocol_fee_safe=protocol_safe,
        )
        errors = [e.message for e in report.errors]
        self.assertTrue(any("Missing protocol fee" in m for m in errors))

    def test_remaining_transfer_to_protocol_safe_labeled_as_partner_tax(self):
        """A second transfer to the DAO safe (after protocol fee is matched) is labelled as partner fee tax."""
        protocol_safe = "0xdaosafe"
        rewards = [_reward("prod-A", "0xAA", "0xTA")]
        native_transfers = [
            _native_t(protocol_safe, 2.038),  # protocol fee
            _native_t(protocol_safe, 0.648),  # partner fee tax
        ]
        report = compare_safe_exports(
            rewards,
            [],
            native_transfers,
            _COW,
            protocol_fee=2.038,
            protocol_fee_safe=protocol_safe,
        )
        self.assertEqual(report.errors, [])
        self.assertEqual(len(report.unmatched_transfers), 1)
        self.assertEqual(len(report.warnings), 1)
        self.assertIn("partner fee tax", report.warnings[0].message)

    def test_without_fee_params_all_unmatched_are_generic_warnings(self):
        protocol_safe = "0xdaosafe"
        rewards = [_reward("prod-A", "0xAA", "0xTA")]
        native_transfers = [_native_t(protocol_safe, 2.038)]
        report = compare_safe_exports(rewards, [], native_transfers, _COW)
        self.assertEqual(len(report.warnings), 1)
        self.assertIn("Unmatched transfer", report.warnings[0].message)
        self.assertNotIn("partner fee tax", report.warnings[0].message)


# ---------------------------------------------------------------------------
# Integration test — 2026-06-16 Arbitrum real data
# ---------------------------------------------------------------------------


class TestArbitrum20260616Integration(unittest.TestCase):
    """Load real CSVs from tests/e2e/2026-06-16-arbitrum and verify them.

    The comparison is expected to find:
    - 0 COW-related errors (all 31 mainnet COW transfers match Dune entries).
    - 3 "missing native transfer" errors for prod-Sector, prod-Rizzolver, and
      prod-Kaisersolver (these solvers have native_token_transfer > threshold in
      Dune but no corresponding row in the Arbitrum Safe export).
    - Several unmatched-transfer warnings for fee/partner transfers that are not
      part of the Dune solver-rewards data.
    """

    @classmethod
    def setUpClass(cls):
        for path in (_DUNE_CSV, _ARB_NATIVE_CSV, _MAINNET_COW_CSV):
            if not os.path.exists(path):
                raise unittest.SkipTest(f"Example CSV not present: {path}")

        from src.verification.compare_output_files import load_dune_rewards

        cls.dune_rewards = load_dune_rewards(_DUNE_CSV)
        cls.cow_transfers = load_safe_transfers(_MAINNET_COW_CSV, _COW)
        cls.native_transfers = load_safe_transfers(_ARB_NATIVE_CSV, _COW)
        cls.report = compare_safe_exports(
            cls.dune_rewards,
            cls.cow_transfers,
            cls.native_transfers,
            _COW,
        )

    def test_dune_csv_has_28_solvers(self):
        self.assertEqual(len(self.dune_rewards), 28)

    def test_mainnet_safe_has_31_cow_transfers(self):
        self.assertEqual(len(self.cow_transfers), 31)

    def test_arbitrum_safe_has_9_native_transfers(self):
        self.assertEqual(len(self.native_transfers), 9)

    def test_no_cow_errors(self):
        cow_errors = [
            e
            for e in self.report.errors
            if "quote reward" in e.message or "solve reward" in e.message
        ]
        self.assertEqual(cow_errors, [], msg=f"Unexpected COW errors: {cow_errors}")

    def test_exactly_three_missing_native_errors(self):
        """Sector, Rizzolver, and Kaisersolver have native in Dune but not in the Safe."""
        native_errors = [
            e for e in self.report.errors if "missing native transfer" in e.message
        ]
        self.assertEqual(len(native_errors), 3)
        names = {e.message.split(":")[0] for e in native_errors}
        self.assertEqual(names, {"prod-Sector", "prod-Rizzolver", "prod-Kaisersolver"})

    def test_total_error_count(self):
        self.assertEqual(len(self.report.errors), 3)

    def test_unmatched_transfers_are_fee_and_partner_transfers(self):
        """The 7 unmatched native transfers are DAO-safe and partner fee transfers."""
        self.assertEqual(len(self.report.unmatched_transfers), 7)
        for t in self.report.unmatched_transfers:
            self.assertEqual(t.token_type, "native")

    def test_all_unmatched_produce_warnings(self):
        unmatched_warnings = [
            w for w in self.report.warnings if "Unmatched transfer" in w.message
        ]
        self.assertEqual(len(unmatched_warnings), 7)

    def test_all_cow_transfers_accounted_for(self):
        """After matching, no COW transfers should remain unmatched."""
        unmatched_cow = [
            t for t in self.report.unmatched_transfers if t.token_type == "erc20"
        ]
        self.assertEqual(unmatched_cow, [])

    def test_cow_totals_are_positive(self):
        self.assertGreater(self.report.totals.quote, 0)
        self.assertGreater(self.report.totals.solve, 0)

    def test_native_solver_transfers_matched(self):
        """OKX and BitgetWallet native transfers should be matched (native total > 0)."""
        self.assertGreater(self.report.totals.native, 0)


if __name__ == "__main__":
    unittest.main()
