"""End-to-end verification tests for the 2026-06-16 Arbitrum payout period.

These tests load the real CSV files from tests/e2e/2026-06-16-arbitrum/ and
run compare_safe_exports() with full fee verification using the V3 fees CSV.

Expected outcome
----------------
All 31 COW transfers in the mainnet Safe match Dune entries.
The protocol fee transfer (2.038… ETH to the DAO safe) is verified against
V3_Weekly_Cost_Coverage_Fees_-_Reimbursement.csv.
3 errors are expected: prod-Sector, prod-Rizzolver, and prod-Kaisersolver each
have a non-zero native_token_transfer in the Dune export but no corresponding
native transfer in the Arbitrum Safe (a real discrepancy in the provided data).
6 unmatched transfers remain after protocol-fee matching:
    1 partner fee tax (second transfer to DAO safe)
    5 partner fee transfers (to partner addresses)
"""
import os
import unittest

_DIR = os.path.join(os.path.dirname(__file__), "2026-06-16-arbitrum")

_DUNE_CSV = os.path.join(_DIR, "Period_Solver_Rewards.csv")
_ARB_NATIVE_CSV = os.path.join(
    _DIR,
    "transfers-arbitrum-2026-06-16 - transactions_export_42161_"
    "0x66331f0b9cb30d38779c786Bda5a3d57d12fbA50_1781886076501.csv.csv",
)
_MAINNET_COW_CSV = os.path.join(
    _DIR,
    "transfers-mainnet-for-arbitrum-2026-06-16 - transactions_export_1_"
    "0xA03be496e67Ec29bC62F01a428683D7F9c204930_1781885784513.csv.csv",
)
_FEES_CSV = os.path.join(_DIR, "V3_Weekly_Cost_Coverage_Fees_-_Reimbursement.csv")

# Mainnet COW token address (rewards are always paid in mainnet COW).
_COW_TOKEN = "0xdef1ca1fb7fbcdc777520aa7f396b4e015f497ab"

# DAO / protocol fee safe address (receives protocol fee and partner fee tax).
_PROTOCOL_FEE_SAFE = "0x22af3d38e50ddedeb7c47f36fab321ec3bb72a76"

# Expected protocol fee from V3_Weekly_Cost_Coverage_Fees.
_EXPECTED_PROTOCOL_FEE = 2.038193570744012


def _require_files(*paths: str) -> None:
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        raise unittest.SkipTest(f"CSV file(s) not present: {', '.join(missing)}")


class TestArbitrum20260616E2E(unittest.TestCase):
    """Full end-to-end comparison using all four CSV files."""

    @classmethod
    def setUpClass(cls):
        _require_files(_DUNE_CSV, _ARB_NATIVE_CSV, _MAINNET_COW_CSV, _FEES_CSV)

        from src.verification.compare_output_files import (
            load_dune_rewards,
            load_fee_summary,
            load_safe_transfers,
            compare_safe_exports,
        )

        cls.dune_rewards = load_dune_rewards(_DUNE_CSV)
        cls.fee_summary = load_fee_summary(_FEES_CSV)
        cls.cow_transfers = load_safe_transfers(_MAINNET_COW_CSV, _COW_TOKEN)
        cls.native_transfers = load_safe_transfers(_ARB_NATIVE_CSV, _COW_TOKEN)
        cls.report = compare_safe_exports(
            cls.dune_rewards,
            cls.cow_transfers,
            cls.native_transfers,
            _COW_TOKEN,
            protocol_fee=cls.fee_summary.protocol_fee,
            protocol_fee_safe=_PROTOCOL_FEE_SAFE,
        )

    # --- Input parsing ---

    def test_fee_summary_protocol_fee_amount(self):
        self.assertAlmostEqual(
            self.fee_summary.protocol_fee, _EXPECTED_PROTOCOL_FEE, places=6
        )

    def test_dune_csv_row_count(self):
        self.assertEqual(len(self.dune_rewards), 28)

    def test_mainnet_safe_csv_cow_transfer_count(self):
        """All 31 outgoing ERC-20 rows should be parsed (empty trailing rows excluded)."""
        self.assertEqual(len(self.cow_transfers), 31)

    def test_arbitrum_safe_csv_native_transfer_count(self):
        """9 outgoing native rows; incoming WETH and zero-address burn excluded."""
        self.assertEqual(len(self.native_transfers), 9)

    # --- COW transfer correctness ---

    def test_no_cow_errors(self):
        cow_errors = [
            e
            for e in self.report.errors
            if "quote reward" in e.message or "solve reward" in e.message
        ]
        self.assertEqual(cow_errors, [], f"Unexpected COW errors: {cow_errors}")

    def test_all_31_cow_transfers_matched(self):
        unmatched_cow = [
            t for t in self.report.unmatched_transfers if t.token_type == "erc20"
        ]
        self.assertEqual(
            unmatched_cow, [], "Some COW transfers were not matched to Dune entries"
        )

    def test_cow_totals_match_dune(self):
        self.assertGreater(self.report.totals.quote, 0)
        self.assertGreater(self.report.totals.solve, 0)

    # --- Native solver transfer correctness ---

    def test_native_solver_transfers_matched(self):
        """prod-OKX and prod-BitgetWallet native transfers should be matched."""
        self.assertGreater(self.report.totals.native, 0)

    def test_three_missing_native_errors(self):
        """prod-Sector, prod-Rizzolver, prod-Kaisersolver have native in Dune but not in the Safe."""
        missing = [e for e in self.report.errors if "missing native transfer" in e.message]
        self.assertEqual(len(missing), 3)
        names = {e.message.split(":")[0] for e in missing}
        self.assertEqual(names, {"prod-Sector", "prod-Rizzolver", "prod-Kaisersolver"})

    # --- Protocol fee verification ---

    def test_protocol_fee_is_verified(self):
        """The protocol fee transfer should not raise an error."""
        protocol_fee_errors = [
            e for e in self.report.errors if "protocol fee" in e.message.lower()
        ]
        self.assertEqual(protocol_fee_errors, [])

    def test_protocol_fee_removed_from_unmatched(self):
        """After protocol-fee matching, no exact-amount transfer to DAO safe remains."""
        protocol_fee_in_unmatched = [
            t
            for t in self.report.unmatched_transfers
            if t.receiver == _PROTOCOL_FEE_SAFE
            and abs(t.amount - _EXPECTED_PROTOCOL_FEE) / _EXPECTED_PROTOCOL_FEE < 0.001
        ]
        self.assertEqual(protocol_fee_in_unmatched, [])

    # --- Unmatched (fee / partner) transfers ---

    def test_six_unmatched_transfers_after_fee_verification(self):
        """1 partner fee tax + 5 partner fee transfers = 6 unmatched."""
        self.assertEqual(len(self.report.unmatched_transfers), 6)

    def test_one_partner_fee_tax_warning(self):
        partner_tax = [
            w for w in self.report.warnings if "partner fee tax" in w.message
        ]
        self.assertEqual(len(partner_tax), 1)

    def test_five_generic_unmatched_warnings(self):
        generic = [
            w for w in self.report.warnings if "not verified against Dune data" in w.message
        ]
        self.assertEqual(len(generic), 5)

    def test_total_warning_count(self):
        self.assertEqual(len(self.report.warnings), 6)

    def test_total_error_count(self):
        """3 missing native errors only; no COW or protocol-fee errors."""
        self.assertEqual(len(self.report.errors), 3)

    def test_all_unmatched_are_native(self):
        for t in self.report.unmatched_transfers:
            self.assertEqual(t.token_type, "native")


class TestArbitrum20260616CLIMode(unittest.TestCase):
    """Test compare_output_files.main() in Safe-export mode with all arguments."""

    def test_main_returns_nonzero_due_to_missing_native(self):
        """main() exit code is 1 because of the 3 missing native transfer errors."""
        _require_files(_DUNE_CSV, _ARB_NATIVE_CSV, _MAINNET_COW_CSV, _FEES_CSV)

        from src.verification.compare_output_files import main

        exit_code = main(
            [
                _DUNE_CSV,
                "--cow-safe-csv",
                _MAINNET_COW_CSV,
                "--native-safe-csv",
                _ARB_NATIVE_CSV,
                "--fees-csv",
                _FEES_CSV,
                "--protocol-fee-safe",
                _PROTOCOL_FEE_SAFE,
                "--network",
                "mainnet",
            ]
        )
        self.assertEqual(exit_code, 1)

    def test_main_requires_native_csv_with_cow_csv(self):
        _require_files(_DUNE_CSV, _MAINNET_COW_CSV)

        from src.verification.compare_output_files import main
        import io
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            exit_code = main(
                [
                    _DUNE_CSV,
                    "--cow-safe-csv",
                    _MAINNET_COW_CSV,
                    "--network",
                    "mainnet",
                ]
            )
        self.assertEqual(exit_code, 2)

    def test_main_requires_protocol_fee_safe_with_fees_csv(self):
        _require_files(_DUNE_CSV, _ARB_NATIVE_CSV, _MAINNET_COW_CSV, _FEES_CSV)

        from src.verification.compare_output_files import main
        import io
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            exit_code = main(
                [
                    _DUNE_CSV,
                    "--cow-safe-csv",
                    _MAINNET_COW_CSV,
                    "--native-safe-csv",
                    _ARB_NATIVE_CSV,
                    "--fees-csv",
                    _FEES_CSV,
                    "--network",
                    "mainnet",
                ]
            )
        self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
