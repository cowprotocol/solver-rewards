"""
Script to generate the CSV Airdrop file for Solver Rewards over an Accounting Period
"""

from __future__ import annotations

import os
import ssl
from dataclasses import asdict

import certifi
from dune_client.client import DuneClient
from dune_client.file.interface import FileIO
from eth_typing import URI
from gnosis.eth.ethereum_client import EthereumClient
from slack.web.client import WebClient

from src.config import AccountingConfig, Network
from src.fetch.dune import DuneFetcher
from src.fetch.payouts import construct_payouts
from src.logger import log_saver, set_log
from src.models.accounting_period import AccountingPeriod
from src.models.transfer import Transfer, CSVTransfer
from src.multisend import post_multisend, prepend_unwrap_if_necessary
from src.pg_client import MultiInstanceDBFetcher
from src.slack_utils import post_to_slack
from src.utils.print_store import Category, PrintStore
from src.utils.script_args import generic_script_init

log = set_log(__name__)


def manual_propose(
    transfers: list[Transfer],
    period: AccountingPeriod,
    config: AccountingConfig,
) -> None:
    """
    Entry point to manual creation of rewards payout transaction.
    This function generates the CSV transfer file to be pasted into the COW Safe app
    """
    print(
        f"Please double check the batches with unusual slippage: "
        f"{period.unusual_slippage_url()}"
    )
    csv_transfers = [asdict(CSVTransfer.from_transfer(t)) for t in transfers]
    FileIO(config.io_config.csv_output_dir).write_csv(
        csv_transfers, f"transfers-{period}.csv"
    )

    print(Transfer.summarize(transfers))
    print("Please cross check these results with the dashboard linked above.\n")


def auto_propose(
    transfers: list[Transfer],
    log_saver_obj: PrintStore,
    slack_client: WebClient,
    dry_run: bool,
    config: AccountingConfig,
) -> None:
    """
    Entry point auto creation of rewards payout transaction.
    This function encodes the multisend of reward transfers and posts
    the transaction to the COW TEAM SAFE from the proposer account.
    """
    # Check for required env vars early
    # so not to wait for query execution to realize it's not available.
    signing_key = config.payment_config.signing_key
    assert signing_key is not None

    client = EthereumClient(URI(config.node_config.node_url))

    log_saver_obj.print(Transfer.summarize(transfers), category=Category.TOTALS)
    transactions = prepend_unwrap_if_necessary(
        client,
        config.payment_config.payment_safe_address,
        wrapped_native_token=config.payment_config.weth_address,
        transactions=[t.as_multisend_tx() for t in transfers],
    )
    if len(transactions) > len(transfers):
        log_saver_obj.print("Prepended WETH unwrap", Category.GENERAL)

    log_saver_obj.print(
        "Instructions for verifying the payout transaction can be found at\n"
        f"{config.payment_config.verification_docs_url}",
        category=Category.GENERAL,
    )

    if not dry_run:
        slack_channel = config.io_config.slack_channel
        assert slack_channel is not None

        nonce = post_multisend(
            safe_address=config.payment_config.payment_safe_address,
            transactions=transactions,
            network=config.payment_config.network,
            signing_key=signing_key,
            client=client,
        )
        post_to_slack(
            slack_client,
            channel=slack_channel,
            message=(
                f"Solver Rewards transaction with nonce {nonce} pending signatures.\n"
                f"To sign and execute, visit:\n{config.payment_config.safe_queue_url}\n"
                f"More details in thread"
            ),
            sub_messages=log_saver_obj.get_values(),
        )


def main() -> None:
    """Generate transfers for an accounting period"""

    args = generic_script_init(description="Fetch Complete Reimbursement")

    config = AccountingConfig.from_network(Network(os.environ["NETWORK"]))

    accounting_period = AccountingPeriod(args.start, length_days=1)

    orderbook = MultiInstanceDBFetcher(
        [config.orderbook_config.prod_db_url, config.orderbook_config.barn_db_url]
    )
    dune = DuneFetcher(
        dune=DuneClient(config.dune_config.dune_api_key),
        period=accounting_period,
    )

    log.info(
        f"Blockrange for accounting period {accounting_period} is from {dune.start_block} to "
        f"{dune.end_block}."
    )

    log_saver.print(
        f"The data aggregated can be visualized at\n{accounting_period.dashboard_url()}",
        category=Category.GENERAL,
    )

    payout_transfers_temp = construct_payouts(
        orderbook=orderbook,
        dune=dune,
        ignore_slippage_flag=args.ignore_slippage,
        config=config,
    )

    payout_transfers = []
    for tr in payout_transfers_temp:
        if tr.token is None:
            if tr.amount_wei >= args.min_transfer_amount_wei:
                payout_transfers.append(tr)
        else:
            if tr.amount_wei >= args.min_transfer_amount_cow_atoms:
                payout_transfers.append(tr)

    if args.post_tx:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        slack_client = WebClient(
            token=config.io_config.slack_token,
            # https://stackoverflow.com/questions/59808346/python-3-slack-client-ssl-sslcertverificationerror
            ssl=ssl_context,
        )
        auto_propose(
            transfers=payout_transfers,
            log_saver_obj=log_saver,
            slack_client=slack_client,
            dry_run=args.dry_run,
            config=config,
        )
    else:
        manual_propose(transfers=payout_transfers, period=dune.period, config=config)


if __name__ == "__main__":
    main()
